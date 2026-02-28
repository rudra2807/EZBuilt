"""
Property-based tests for Deployment API endpoints.

This test validates properties related to the deployment API endpoints:
- Property 5: Deployment Initial State
- Property 6: AWS Connection Validation

Uses Hypothesis for property-based testing with minimum 100 iterations.
"""

import pytest
import uuid
import os
import sys
import asyncio
from hypothesis import given, strategies as st, settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import HTTPException

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import User, TerraformPlan, AWSIntegration, Deployment, DeploymentStatus, IntegrationStatus
from src.database.repositories import DeploymentRepository
from src.apis.routes_deployment import deploy, DeployRequest
from unittest.mock import AsyncMock, MagicMock


# Use local test database
DATABASE_URL = "postgresql+asyncpg://postgres:master@localhost:5432/ezbuilt_test"


async def create_db_session():
    """Create a database session for testing"""
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    user_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    plan_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
)
async def test_property_deployment_initial_state(user_suffix, plan_suffix):
    """
    Property 5: Deployment Initial State
    
    For any valid deploy request (with valid terraform_plan_id and aws_connection_id 
    belonging to the user), when a deployment is created, the initial status should 
    always be "started".
    """
    # Create a fresh database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a unique user
            user_id = f"test-user-{uuid.uuid4()}-{user_suffix}"
            email = f"user-{uuid.uuid4()}-{user_suffix}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration for the user
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
            
            # Create terraform plan for the user
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Test requirements {plan_suffix}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment using the repository
            deployment_repo = DeploymentRepository(db_session)
            
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Property: The initial status should ALWAYS be "started"
            assert deployment.status == DeploymentStatus.STARTED, \
                f"Expected initial deployment status to be STARTED, but got {deployment.status}"
            
            # Additional invariants that should hold for initial state
            assert deployment.id is not None, "Deployment should have an ID"
            assert deployment.user_id == user_id, "Deployment should belong to the correct user"
            assert deployment.terraform_plan_id == plan.id, "Deployment should reference the correct plan"
            assert deployment.aws_connection_id == aws_conn.id, "Deployment should reference the correct AWS connection"
            assert deployment.output is None, "Initial deployment should have no output"
            assert deployment.error_message is None, "Initial deployment should have no error message"
            assert deployment.created_at is not None, "Deployment should have a created_at timestamp"
            assert deployment.updated_at is not None, "Deployment should have an updated_at timestamp"
            assert deployment.completed_at is None, "Initial deployment should not have a completed_at timestamp"
        
        finally:
            # Cleanup: rollback any changes
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    user_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    plan_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    # Generate non-connected status (only PENDING is available besides CONNECTED)
    aws_status=st.sampled_from([IntegrationStatus.PENDING])
)
async def test_property_aws_connection_validation(user_suffix, plan_suffix, aws_status):
    """
    Property 6: AWS Connection Validation
    
    For any deploy request, when the aws_connection status is not "connected", 
    the system should reject the request with a 400 Bad Request error.
    """
    # Create a fresh database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a unique user
            user_id = f"test-user-{uuid.uuid4()}-{user_suffix}"
            email = f"user-{uuid.uuid4()}-{user_suffix}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration with NON-CONNECTED status
            aws_conn = AWSIntegration(
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=aws_status  # This is NOT CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            await db_session.refresh(aws_conn)
            
            # Create terraform plan for the user
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Test requirements {plan_suffix}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deploy request
            request = DeployRequest(
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Create mock background tasks
            background_tasks = MagicMock()
            
            # Property: Attempting to deploy with non-connected AWS connection should raise 400 error
            with pytest.raises(HTTPException) as exc_info:
                await deploy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            # Verify the error is 400 Bad Request
            assert exc_info.value.status_code == 400, \
                f"Expected status code 400 for non-connected AWS connection, but got {exc_info.value.status_code}"
            
            # Verify the error message mentions the status issue
            assert "must be connected" in exc_info.value.detail.lower(), \
                f"Expected error message to mention 'must be connected', but got: {exc_info.value.detail}"
            
            # Verify the error message includes the actual status
            assert aws_status.value in exc_info.value.detail.lower(), \
                f"Expected error message to include status '{aws_status.value}', but got: {exc_info.value.detail}"
            
            # Verify no deployment was created
            deployment_repo = DeploymentRepository(db_session)
            user_deployments = await deployment_repo.get_user_deployments(user_id)
            assert len(user_deployments) == 0, \
                f"Expected no deployments to be created for non-connected AWS connection, but found {len(user_deployments)}"
        
        finally:
            # Cleanup: rollback any changes
            await db_session.rollback()
    
    await engine.dispose()



@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    user_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    plan_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    # Generate non-success deployment statuses
    deployment_status=st.sampled_from([
        DeploymentStatus.STARTED,
        DeploymentStatus.RUNNING,
        DeploymentStatus.FAILED,
        DeploymentStatus.DESTROYED,
        DeploymentStatus.DESTROY_FAILED
    ])
)
async def test_property_destroy_status_validation(user_suffix, plan_suffix, deployment_status):
    """
    Property 8: Destroy Status Validation
    
    For any destroy request, when the deployment status is not "success", 
    the system should reject the request with a 400 Bad Request error 
    indicating the current status.
    """
    # Create a fresh database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a unique user
            user_id = f"test-user-{uuid.uuid4()}-{user_suffix}"
            email = f"user-{uuid.uuid4()}-{user_suffix}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration for the user
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
            
            # Create terraform plan for the user
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Test requirements {plan_suffix}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment with NON-SUCCESS status
            from src.database.models import Deployment
            deployment = Deployment(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=deployment_status  # This is NOT SUCCESS
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            # Create destroy request
            from src.apis.routes_deployment import destroy, DestroyRequest
            request = DestroyRequest(deployment_id=deployment.id)
            
            # Create mock background tasks
            background_tasks = MagicMock()
            
            # Property: Attempting to destroy deployment with non-success status should raise 400 error
            with pytest.raises(HTTPException) as exc_info:
                await destroy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            # Verify the error is 400 Bad Request
            assert exc_info.value.status_code == 400, \
                f"Expected status code 400 for deployment with status {deployment_status.value}, but got {exc_info.value.status_code}"
            
            # Verify the error message mentions "cannot destroy"
            assert "cannot destroy" in exc_info.value.detail.lower(), \
                f"Expected error message to mention 'cannot destroy', but got: {exc_info.value.detail}"
            
            # Verify the error message mentions "must be success"
            assert "must be success" in exc_info.value.detail.lower(), \
                f"Expected error message to mention 'must be success', but got: {exc_info.value.detail}"
            
            # Verify the error message includes the actual status
            assert deployment_status.value in exc_info.value.detail.lower(), \
                f"Expected error message to include status '{deployment_status.value}', but got: {exc_info.value.detail}"
            
            # Verify the deployment status was NOT changed
            await db_session.refresh(deployment)
            assert deployment.status == deployment_status, \
                f"Expected deployment status to remain {deployment_status.value}, but it changed to {deployment.status.value}"
            
            # Verify no background task was enqueued
            background_tasks.add_task.assert_not_called()
        
        finally:
            # Cleanup: rollback any changes
            await db_session.rollback()
    
    await engine.dispose()



@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    owner_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    other_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    plan_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
)
async def test_property_unauthorized_access_returns_403(owner_suffix, other_suffix, plan_suffix):
    """
    Property 18: Unauthorized Access Returns 403
    
    For any user attempting to access (view or destroy) a deployment that does 
    not belong to them, the system should return a 403 Forbidden error.
    """
    # Create a fresh database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create the OWNER user who owns the deployment
            owner_user_id = f"test-owner-{uuid.uuid4()}-{owner_suffix}"
            owner_email = f"owner-{uuid.uuid4()}-{owner_suffix}@example.com"
            
            owner_user = User(user_id=owner_user_id, email=owner_email)
            db_session.add(owner_user)
            await db_session.commit()
            
            # Create the OTHER user who will try to access the deployment
            other_user_id = f"test-other-{uuid.uuid4()}-{other_suffix}"
            other_email = f"other-{uuid.uuid4()}-{other_suffix}@example.com"
            
            other_user = User(user_id=other_user_id, email=other_email)
            db_session.add(other_user)
            await db_session.commit()
            
            # Create AWS integration for the owner
            aws_conn = AWSIntegration(
                user_id=owner_user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            await db_session.refresh(aws_conn)
            
            # Create terraform plan for the owner
            plan = TerraformPlan(
                user_id=owner_user_id,
                original_requirements=f"Test requirements {plan_suffix}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{owner_user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment owned by the OWNER user with SUCCESS status
            from src.database.models import Deployment
            deployment = Deployment(
                user_id=owner_user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.SUCCESS
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            # TEST 1: OTHER user tries to GET deployment status (should get 403)
            from src.apis.routes_deployment import get_deployment_status
            
            with pytest.raises(HTTPException) as exc_info:
                await get_deployment_status(
                    deployment_id=deployment.id,
                    user_id=other_user_id,  # Different user trying to access
                    db=db_session
                )
            
            # Property: Should return 403 Forbidden
            assert exc_info.value.status_code == 403, \
                f"Expected status code 403 when other user tries to view deployment, but got {exc_info.value.status_code}"
            
            # Verify error message indicates access denial
            assert "does not belong to user" in exc_info.value.detail.lower(), \
                f"Expected error message to indicate access denial, but got: {exc_info.value.detail}"
            
            # TEST 2: OTHER user tries to DESTROY deployment (should get 403)
            from src.apis.routes_deployment import destroy, DestroyRequest
            
            destroy_request = DestroyRequest(deployment_id=deployment.id)
            background_tasks = MagicMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await destroy(
                    request=destroy_request,
                    background_tasks=background_tasks,
                    user_id=other_user_id,  # Different user trying to destroy
                    db=db_session
                )
            
            # Property: Should return 403 Forbidden
            assert exc_info.value.status_code == 403, \
                f"Expected status code 403 when other user tries to destroy deployment, but got {exc_info.value.status_code}"
            
            # Verify error message indicates access denial
            assert "does not belong to user" in exc_info.value.detail.lower(), \
                f"Expected error message to indicate access denial, but got: {exc_info.value.detail}"
            
            # Verify no background task was enqueued
            background_tasks.add_task.assert_not_called()
            
            # Verify deployment status was NOT changed
            await db_session.refresh(deployment)
            assert deployment.status == DeploymentStatus.SUCCESS, \
                f"Expected deployment status to remain SUCCESS after unauthorized destroy attempt, but got {deployment.status.value}"
            
            # TEST 3: Verify OWNER can still access their own deployment (sanity check)
            # This ensures the 403 is specifically for unauthorized access, not a general error
            deployment_response = await get_deployment_status(
                deployment_id=deployment.id,
                user_id=owner_user_id,  # Owner accessing their own deployment
                db=db_session
            )
            
            # Should succeed without exception
            assert deployment_response.id == deployment.id, \
                "Owner should be able to access their own deployment"
            assert deployment_response.status == DeploymentStatus.SUCCESS.value, \
                "Owner should see correct deployment status"
        
        finally:
            # Cleanup: rollback any changes
            await db_session.rollback()
    
    await engine.dispose()
