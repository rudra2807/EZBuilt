"""
Integration tests for end-to-end deployment flow.

This test validates the complete deployment flow from API request to database update:
- Complete deploy flow from API request to database update
- Complete destroy flow from API request to database update
- Deployment status transitions through state machine
- Mock S3 downloads and Terraform subprocess calls
"""

import pytest
import uuid
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import User, TerraformPlan, AWSIntegration, Deployment, DeploymentStatus, IntegrationStatus
from src.database.repositories import DeploymentRepository
from src.apis.routes_deployment import deploy, destroy, DeployRequest, DestroyRequest
from src.services.deployment_service import execute_terraform_apply, execute_terraform_destroy


# Use local test database
DATABASE_URL = "postgresql+asyncpg://postgres:master@localhost:5432/ezbuilt_test"


async def create_test_data(db_session):
    """Helper function to create test user, plan, and AWS connection"""
    # Create user
    user_id = f"test-user-{uuid.uuid4()}"
    email = f"user-{uuid.uuid4()}@example.com"
    
    user = User(user_id=user_id, email=email)
    db_session.add(user)
    await db_session.commit()
    
    # Create AWS integration
    aws_conn = AWSIntegration(
        user_id=user_id,
        external_id=f"ext-{uuid.uuid4()}",
        aws_account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/TestRole",
        status=IntegrationStatus.CONNECTED
    )
    db_session.add(aws_conn)
    await db_session.commit()
    await db_session.refresh(aws_conn)
    
    # Create terraform plan
    plan = TerraformPlan(
        user_id=user_id,
        original_requirements="Test infrastructure requirements",
        structured_requirements={"resources": ["ec2", "s3"]},
        s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
        status="completed"
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    
    return user_id, plan, aws_conn


@pytest.mark.asyncio
async def test_complete_deploy_flow():
    """
    Test complete deploy flow from API request to database update.
    
    Flow:
    1. User makes POST /api/deploy request
    2. API validates request and creates deployment record
    3. Background task executes Terraform apply
    4. Database is updated with final status
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id, plan, aws_conn = await create_test_data(db_session)
            
            # Create deploy request
            request = DeployRequest(
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Mock background tasks
            background_tasks = MagicMock()
            
            # Step 1: Call deploy API endpoint
            response = await deploy(
                request=request,
                background_tasks=background_tasks,
                user_id=user_id,
                db=db_session
            )
            
            # Verify API response
            assert "deployment_id" in response
            assert response["status"] == "started"
            assert "message" in response
            
            deployment_id = uuid.UUID(response["deployment_id"])
            
            # Verify deployment record was created in database
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.get_by_id(deployment_id, user_id)
            
            assert deployment is not None
            assert deployment.status == DeploymentStatus.STARTED
            assert deployment.user_id == user_id
            assert deployment.terraform_plan_id == plan.id
            assert deployment.aws_connection_id == aws_conn.id
            assert deployment.output is None
            assert deployment.error_message is None
            assert deployment.completed_at is None
            
            # Verify background task was enqueued
            background_tasks.add_task.assert_called_once()
            
            # Step 2: Simulate background task execution with mocked Terraform
            with patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
                 patch('src.services.deployment_service.assume_role') as mock_assume, \
                 patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
                 patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
                
                # Mock successful S3 download
                mock_download.return_value = ['main.tf', 'variables.tf']
                
                # Mock successful role assumption
                mock_assume.return_value = {
                    'AccessKeyId': 'test-key',
                    'SecretAccessKey': 'test-secret',
                    'SessionToken': 'test-token'
                }
                
                # Mock successful Terraform commands
                mock_subprocess.side_effect = [
                    MagicMock(returncode=0, stdout='Terraform initialized', stderr=''),  # init
                    MagicMock(returncode=0, stdout='Plan: 2 to add, 0 to change', stderr=''),  # plan
                    MagicMock(returncode=0, stdout='Apply complete! Resources: 2 added', stderr='')  # apply
                ]
                
                # Execute background task
                await execute_terraform_apply(
                    deployment_id=deployment_id,
                    terraform_plan_id=plan.id,
                    s3_prefix=plan.s3_prefix,
                    role_arn=aws_conn.role_arn,
                    external_id=aws_conn.external_id,
                    db=db_session
                )
            
            # Step 3: Verify final database state
            await db_session.refresh(deployment)
            
            assert deployment.status == DeploymentStatus.SUCCESS
            assert deployment.output is not None
            assert 'Apply complete' in deployment.output
            assert deployment.error_message is None
            assert deployment.completed_at is not None
            
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_destroy_flow():
    """
    Test complete destroy flow from API request to database update.
    
    Flow:
    1. User makes POST /api/destroy request
    2. API validates deployment status is SUCCESS
    3. Background task executes Terraform destroy
    4. Database is updated with final status
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id, plan, aws_conn = await create_test_data(db_session)
            
            # Create a deployment with SUCCESS status
            deployment = Deployment(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.SUCCESS,
                output="Previous apply output"
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            deployment_id = deployment.id
            
            # Create destroy request
            request = DestroyRequest(deployment_id=deployment_id)
            
            # Mock background tasks
            background_tasks = MagicMock()
            
            # Step 1: Call destroy API endpoint
            response = await destroy(
                request=request,
                background_tasks=background_tasks,
                user_id=user_id,
                db=db_session
            )
            
            # Verify API response
            assert "deployment_id" in response
            assert response["status"] == "started"
            assert "message" in response
            
            # Verify deployment status was updated to STARTED
            await db_session.refresh(deployment)
            assert deployment.status == DeploymentStatus.STARTED
            
            # Verify background task was enqueued
            background_tasks.add_task.assert_called_once()
            
            # Step 2: Simulate background task execution with mocked Terraform
            # Create temp directory for the test
            tmp_dir = f"/tmp/{deployment_id}"
            os.makedirs(tmp_dir, exist_ok=True)
            
            try:
                with patch('src.services.deployment_service.assume_role') as mock_assume, \
                     patch('src.services.deployment_service.subprocess.run') as mock_subprocess:
                    
                    # Mock successful role assumption
                    mock_assume.return_value = {
                        'AccessKeyId': 'test-key',
                        'SecretAccessKey': 'test-secret',
                        'SessionToken': 'test-token'
                    }
                    
                    # Mock successful Terraform destroy
                    mock_subprocess.return_value = MagicMock(
                        returncode=0,
                        stdout='Destroy complete! Resources: 2 destroyed',
                        stderr=''
                    )
                    
                    # Execute background task
                    await execute_terraform_destroy(
                        deployment_id=deployment_id,
                        role_arn=aws_conn.role_arn,
                        external_id=aws_conn.external_id,
                        db=db_session
                    )
            finally:
                # Cleanup temp directory if it still exists
                if os.path.exists(tmp_dir):
                    import shutil
                    shutil.rmtree(tmp_dir)
            
            # Step 3: Verify final database state
            await db_session.refresh(deployment)
            
            assert deployment.status == DeploymentStatus.DESTROYED
            assert deployment.output is not None
            assert 'Destroy complete' in deployment.output
            assert deployment.error_message is None
            assert deployment.completed_at is not None
            
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_deployment_status_transitions():
    """
    Test deployment status transitions through state machine.
    
    Verifies the state machine transitions:
    - STARTED → RUNNING → SUCCESS (for successful apply)
    - STARTED → RUNNING → FAILED (for failed apply)
    - SUCCESS → STARTED → RUNNING → DESTROYED (for successful destroy)
    - SUCCESS → STARTED → RUNNING → DESTROY_FAILED (for failed destroy)
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id, plan, aws_conn = await create_test_data(db_session)
            
            # Test Case 1: Successful apply (STARTED → RUNNING → SUCCESS)
            deployment_repo = DeploymentRepository(db_session)
            deployment1 = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Verify initial state
            assert deployment1.status == DeploymentStatus.STARTED
            
            # Simulate background task updating to RUNNING
            await deployment_repo.update_status(deployment1.id, DeploymentStatus.RUNNING)
            await db_session.refresh(deployment1)
            assert deployment1.status == DeploymentStatus.RUNNING
            assert deployment1.completed_at is None
            
            # Simulate successful completion
            await deployment_repo.update_status(
                deployment1.id,
                DeploymentStatus.SUCCESS,
                output="Apply successful"
            )
            await db_session.refresh(deployment1)
            assert deployment1.status == DeploymentStatus.SUCCESS
            assert deployment1.output == "Apply successful"
            assert deployment1.completed_at is not None
            
            # Test Case 2: Failed apply (STARTED → RUNNING → FAILED)
            deployment2 = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            assert deployment2.status == DeploymentStatus.STARTED
            
            await deployment_repo.update_status(deployment2.id, DeploymentStatus.RUNNING)
            await db_session.refresh(deployment2)
            assert deployment2.status == DeploymentStatus.RUNNING
            
            # Simulate failure
            await deployment_repo.update_status(
                deployment2.id,
                DeploymentStatus.FAILED,
                error_message="Terraform apply failed"
            )
            await db_session.refresh(deployment2)
            assert deployment2.status == DeploymentStatus.FAILED
            assert deployment2.error_message == "Terraform apply failed"
            assert deployment2.completed_at is not None
            
            # Test Case 3: Successful destroy (SUCCESS → STARTED → RUNNING → DESTROYED)
            # Use deployment1 which is in SUCCESS state
            await deployment_repo.update_status(deployment1.id, DeploymentStatus.STARTED)
            await db_session.refresh(deployment1)
            assert deployment1.status == DeploymentStatus.STARTED
            
            await deployment_repo.update_status(deployment1.id, DeploymentStatus.RUNNING)
            await db_session.refresh(deployment1)
            assert deployment1.status == DeploymentStatus.RUNNING
            
            await deployment_repo.update_status(
                deployment1.id,
                DeploymentStatus.DESTROYED,
                output="Destroy successful"
            )
            await db_session.refresh(deployment1)
            assert deployment1.status == DeploymentStatus.DESTROYED
            assert deployment1.output == "Destroy successful"
            assert deployment1.completed_at is not None
            
            # Test Case 4: Failed destroy (SUCCESS → STARTED → RUNNING → DESTROY_FAILED)
            deployment3 = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Set to SUCCESS first
            await deployment_repo.update_status(
                deployment3.id,
                DeploymentStatus.SUCCESS,
                output="Initial apply"
            )
            await db_session.refresh(deployment3)
            
            # Start destroy
            await deployment_repo.update_status(deployment3.id, DeploymentStatus.STARTED)
            await db_session.refresh(deployment3)
            assert deployment3.status == DeploymentStatus.STARTED
            
            await deployment_repo.update_status(deployment3.id, DeploymentStatus.RUNNING)
            await db_session.refresh(deployment3)
            assert deployment3.status == DeploymentStatus.RUNNING
            
            # Simulate destroy failure
            await deployment_repo.update_status(
                deployment3.id,
                DeploymentStatus.DESTROY_FAILED,
                error_message="Terraform destroy failed"
            )
            await db_session.refresh(deployment3)
            assert deployment3.status == DeploymentStatus.DESTROY_FAILED
            assert deployment3.error_message == "Terraform destroy failed"
            assert deployment3.completed_at is not None
            
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_deploy_flow_with_s3_failure():
    """
    Test deploy flow when S3 download fails.
    
    Verifies that S3 failures are properly handled and deployment
    status is updated to FAILED with error message.
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id, plan, aws_conn = await create_test_data(db_session)
            
            # Create deployment
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            deployment_id = deployment.id
            
            # Simulate background task with S3 failure
            with patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
                 patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
                
                # Mock S3 download failure
                from src.services.s3_service import S3ServiceError
                mock_download.side_effect = S3ServiceError("Access denied to S3 bucket")
                
                # Execute background task
                await execute_terraform_apply(
                    deployment_id=deployment_id,
                    terraform_plan_id=plan.id,
                    s3_prefix=plan.s3_prefix,
                    role_arn=aws_conn.role_arn,
                    external_id=aws_conn.external_id,
                    db=db_session
                )
            
            # Verify deployment status was updated to FAILED
            await db_session.refresh(deployment)
            
            assert deployment.status == DeploymentStatus.FAILED
            assert deployment.error_message is not None
            assert "S3 download failed" in deployment.error_message
            assert "Access denied" in deployment.error_message
            assert deployment.completed_at is not None
            
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_deploy_flow_with_terraform_failure():
    """
    Test deploy flow when Terraform command fails.
    
    Verifies that Terraform failures are properly handled and deployment
    status is updated to FAILED with error message.
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id, plan, aws_conn = await create_test_data(db_session)
            
            # Create deployment
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            deployment_id = deployment.id
            
            # Simulate background task with Terraform failure
            with patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
                 patch('src.services.deployment_service.assume_role') as mock_assume, \
                 patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
                 patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
                
                # Mock successful S3 download
                mock_download.return_value = ['main.tf']
                
                # Mock successful role assumption
                mock_assume.return_value = {
                    'AccessKeyId': 'test-key',
                    'SecretAccessKey': 'test-secret',
                    'SessionToken': 'test-token'
                }
                
                # Mock Terraform init success, but apply failure
                mock_subprocess.side_effect = [
                    MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                    MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
                    MagicMock(returncode=1, stdout='', stderr='Error: Resource creation failed')  # apply
                ]
                
                # Execute background task
                await execute_terraform_apply(
                    deployment_id=deployment_id,
                    terraform_plan_id=plan.id,
                    s3_prefix=plan.s3_prefix,
                    role_arn=aws_conn.role_arn,
                    external_id=aws_conn.external_id,
                    db=db_session
                )
            
            # Verify deployment status was updated to FAILED
            await db_session.refresh(deployment)
            
            assert deployment.status == DeploymentStatus.FAILED
            assert deployment.error_message is not None
            assert "Apply failed" in deployment.error_message
            assert "Resource creation failed" in deployment.error_message
            assert deployment.completed_at is not None
            
        finally:
            await db_session.rollback()
    
    await engine.dispose()



# ============================================================================
# Property-Based Tests
# ============================================================================


from hypothesis import given, strategies as st, settings


@st.composite
def deployment_operation_sequence(draw):
    """
    Generate a sequence of deployment operations.
    
    Returns a list of operations representing a valid deployment lifecycle:
    - 'apply_success': Successful apply operation
    - 'apply_failure': Failed apply operation
    - 'destroy_success': Successful destroy operation (only after apply_success)
    - 'destroy_failure': Failed destroy operation (only after apply_success)
    """
    # First operation is always an apply
    first_op = draw(st.sampled_from(['apply_success', 'apply_failure']))
    
    operations = [first_op]
    
    # If first apply succeeded, we can optionally add a destroy operation
    if first_op == 'apply_success':
        has_destroy = draw(st.booleans())
        if has_destroy:
            destroy_op = draw(st.sampled_from(['destroy_success', 'destroy_failure']))
            operations.append(destroy_op)
    
    return operations


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(operations=deployment_operation_sequence())
async def test_property_deployment_state_transitions(operations):
    """
    Property 9: Deployment State Transitions
    
    For any deployment, the status transitions should follow the state machine:
    - New deployments start with "started"
    - Background tasks transition to "running"
    - Successful apply transitions to "success"
    - Failed apply transitions to "failed"
    - Destroy from "success" transitions through "started" → "running" → "destroyed" or "destroy_failed"
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration
            aws_conn = AWSIntegration(
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            await db_session.refresh(aws_conn)
            
            # Create terraform plan
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements="Test requirements",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Property: Initial state must be STARTED
            assert deployment.status == DeploymentStatus.STARTED, \
                "New deployment must start with STARTED status"
            assert deployment.completed_at is None, \
                "New deployment should not have completed_at timestamp"
            
            # Execute operations sequence
            for operation in operations:
                if operation == 'apply_success':
                    # Transition: STARTED → RUNNING
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.RUNNING)
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.RUNNING, \
                        "Deployment should transition to RUNNING"
                    assert deployment.completed_at is None, \
                        "RUNNING deployment should not have completed_at"
                    
                    # Transition: RUNNING → SUCCESS
                    await deployment_repo.update_status(
                        deployment.id,
                        DeploymentStatus.SUCCESS,
                        output="Apply successful"
                    )
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.SUCCESS, \
                        "Successful apply should transition to SUCCESS"
                    assert deployment.output == "Apply successful", \
                        "SUCCESS deployment should have output"
                    assert deployment.completed_at is not None, \
                        "SUCCESS is terminal state and must have completed_at"
                
                elif operation == 'apply_failure':
                    # Transition: STARTED → RUNNING
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.RUNNING)
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.RUNNING
                    
                    # Transition: RUNNING → FAILED
                    await deployment_repo.update_status(
                        deployment.id,
                        DeploymentStatus.FAILED,
                        error_message="Apply failed"
                    )
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.FAILED, \
                        "Failed apply should transition to FAILED"
                    assert deployment.error_message == "Apply failed", \
                        "FAILED deployment should have error_message"
                    assert deployment.completed_at is not None, \
                        "FAILED is terminal state and must have completed_at"
                
                elif operation == 'destroy_success':
                    # Can only destroy from SUCCESS state
                    assert deployment.status == DeploymentStatus.SUCCESS, \
                        "Destroy can only be called on SUCCESS deployments"
                    
                    # Transition: SUCCESS → STARTED (for destroy)
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.STARTED)
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.STARTED
                    
                    # Transition: STARTED → RUNNING
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.RUNNING)
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.RUNNING
                    
                    # Transition: RUNNING → DESTROYED
                    await deployment_repo.update_status(
                        deployment.id,
                        DeploymentStatus.DESTROYED,
                        output="Destroy successful"
                    )
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.DESTROYED, \
                        "Successful destroy should transition to DESTROYED"
                    assert deployment.output == "Destroy successful", \
                        "DESTROYED deployment should have output"
                    assert deployment.completed_at is not None, \
                        "DESTROYED is terminal state and must have completed_at"
                
                elif operation == 'destroy_failure':
                    # Can only destroy from SUCCESS state
                    assert deployment.status == DeploymentStatus.SUCCESS
                    
                    # Transition: SUCCESS → STARTED → RUNNING
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.STARTED)
                    await db_session.refresh(deployment)
                    await deployment_repo.update_status(deployment.id, DeploymentStatus.RUNNING)
                    await db_session.refresh(deployment)
                    
                    # Transition: RUNNING → DESTROY_FAILED
                    await deployment_repo.update_status(
                        deployment.id,
                        DeploymentStatus.DESTROY_FAILED,
                        error_message="Destroy failed"
                    )
                    await db_session.refresh(deployment)
                    
                    assert deployment.status == DeploymentStatus.DESTROY_FAILED, \
                        "Failed destroy should transition to DESTROY_FAILED"
                    assert deployment.error_message == "Destroy failed", \
                        "DESTROY_FAILED deployment should have error_message"
                    assert deployment.completed_at is not None, \
                        "DESTROY_FAILED is terminal state and must have completed_at"
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()



@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    terminal_status=st.sampled_from([
        DeploymentStatus.SUCCESS,
        DeploymentStatus.FAILED,
        DeploymentStatus.DESTROYED,
        DeploymentStatus.DESTROY_FAILED
    ]),
    has_output=st.booleans(),
    has_error=st.booleans()
)
async def test_property_completed_timestamp_on_terminal_states(terminal_status, has_output, has_error):
    """
    Property 10: Completed Timestamp on Terminal States
    
    For any deployment that reaches a terminal state (success, failed, destroyed, destroy_failed),
    the completed_at timestamp should be set to a non-null value.
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup test data
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration
            aws_conn = AWSIntegration(
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            await db_session.refresh(aws_conn)
            
            # Create terraform plan
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements="Test requirements",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Verify initial state has no completed_at
            assert deployment.completed_at is None, \
                "New deployment should not have completed_at timestamp"
            
            # Transition to RUNNING (non-terminal state)
            await deployment_repo.update_status(deployment.id, DeploymentStatus.RUNNING)
            await db_session.refresh(deployment)
            
            # Verify RUNNING state still has no completed_at
            assert deployment.completed_at is None, \
                "RUNNING deployment should not have completed_at timestamp"
            
            # Prepare output/error based on terminal status
            output = "Operation output" if has_output else None
            error_message = "Operation error" if has_error else None
            
            # Transition to terminal state
            await deployment_repo.update_status(
                deployment.id,
                terminal_status,
                output=output,
                error_message=error_message
            )
            await db_session.refresh(deployment)
            
            # Property: Terminal states MUST have completed_at timestamp
            assert deployment.completed_at is not None, \
                f"Terminal state {terminal_status.value} must have completed_at timestamp"
            
            # Verify the timestamp is reasonable (within last minute)
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            time_diff = now - deployment.completed_at.replace(tzinfo=None)
            assert time_diff < timedelta(minutes=1), \
                f"completed_at timestamp should be recent, but was {time_diff} ago"
            
            # Verify status is correct
            assert deployment.status == terminal_status, \
                f"Deployment status should be {terminal_status.value}"
            
            # Verify output/error are set correctly
            if has_output:
                assert deployment.output == output
            if has_error:
                assert deployment.error_message == error_message
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()
