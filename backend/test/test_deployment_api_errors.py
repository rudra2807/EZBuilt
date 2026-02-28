"""
Unit tests for Deployment API endpoint error cases.

Tests error handling for:
- 404 errors for missing resources
- 400 errors for invalid requests
- 403 errors for unauthorized access
- Response structure for status endpoint
"""

import pytest
import uuid
import os
import sys
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import HTTPException

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import User, TerraformPlan, AWSIntegration, Deployment, DeploymentStatus, IntegrationStatus
from src.apis.routes_deployment import deploy, destroy, get_deployment_status, DeployRequest, DestroyRequest

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


# ============================================
# DEPLOY ENDPOINT - 404 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_deploy_terraform_plan_not_found():
    """
    Test deploy endpoint returns 404 when terraform_plan_id does not exist.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
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
            
            # Use non-existent terraform_plan_id
            non_existent_plan_id = uuid.uuid4()
            
            request = DeployRequest(
                terraform_plan_id=non_existent_plan_id,
                aws_connection_id=aws_conn.id
            )
            
            background_tasks = MagicMock()
            
            # Should raise 404 error
            with pytest.raises(HTTPException) as exc_info:
                await deploy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 404
            assert "terraform plan not found" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_deploy_aws_connection_not_found():
    """
    Test deploy endpoint returns 404 when aws_connection_id does not exist.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
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
            
            # Use non-existent aws_connection_id
            non_existent_aws_id = uuid.uuid4()
            
            request = DeployRequest(
                terraform_plan_id=plan.id,
                aws_connection_id=non_existent_aws_id
            )
            
            background_tasks = MagicMock()
            
            # Should raise 404 error
            with pytest.raises(HTTPException) as exc_info:
                await deploy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 404
            assert "aws connection not found" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# DEPLOY ENDPOINT - 400 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_deploy_aws_connection_not_connected():
    """
    Test deploy endpoint returns 400 when AWS connection status is not CONNECTED.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration with PENDING status
            aws_conn = AWSIntegration(
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.PENDING  # NOT CONNECTED
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
            
            request = DeployRequest(
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            background_tasks = MagicMock()
            
            # Should raise 400 error
            with pytest.raises(HTTPException) as exc_info:
                await deploy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 400
            assert "must be connected" in exc_info.value.detail.lower()
            assert "pending" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# DESTROY ENDPOINT - 404 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_destroy_deployment_not_found():
    """
    Test destroy endpoint returns 404 when deployment_id does not exist.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Use non-existent deployment_id
            non_existent_deployment_id = uuid.uuid4()
            
            request = DestroyRequest(deployment_id=non_existent_deployment_id)
            background_tasks = MagicMock()
            
            # Should raise 404 error
            with pytest.raises(HTTPException) as exc_info:
                await destroy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 404
            assert "deployment not found" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# DESTROY ENDPOINT - 400 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_destroy_deployment_invalid_status():
    """
    Test destroy endpoint returns 400 when deployment status is not SUCCESS.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
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
            
            # Create deployment with FAILED status (not SUCCESS)
            deployment = Deployment(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.FAILED
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            request = DestroyRequest(deployment_id=deployment.id)
            background_tasks = MagicMock()
            
            # Should raise 400 error
            with pytest.raises(HTTPException) as exc_info:
                await destroy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 400
            assert "cannot destroy" in exc_info.value.detail.lower()
            assert "must be success" in exc_info.value.detail.lower()
            assert "failed" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# DESTROY ENDPOINT - 403 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_destroy_deployment_unauthorized():
    """
    Test destroy endpoint returns 403 when user tries to destroy another user's deployment.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create owner user
            owner_user_id = f"test-owner-{uuid.uuid4()}"
            owner_email = f"owner-{uuid.uuid4()}@example.com"
            
            owner_user = User(user_id=owner_user_id, email=owner_email)
            db_session.add(owner_user)
            await db_session.commit()
            
            # Create other user
            other_user_id = f"test-other-{uuid.uuid4()}"
            other_email = f"other-{uuid.uuid4()}@example.com"
            
            other_user = User(user_id=other_user_id, email=other_email)
            db_session.add(other_user)
            await db_session.commit()
            
            # Create AWS integration for owner
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
            
            # Create terraform plan for owner
            plan = TerraformPlan(
                user_id=owner_user_id,
                original_requirements="Test requirements",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=f"terraform/{owner_user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment owned by owner with SUCCESS status
            deployment = Deployment(
                user_id=owner_user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.SUCCESS
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            request = DestroyRequest(deployment_id=deployment.id)
            background_tasks = MagicMock()
            
            # Other user tries to destroy owner's deployment - should raise 403
            with pytest.raises(HTTPException) as exc_info:
                await destroy(
                    request=request,
                    background_tasks=background_tasks,
                    user_id=other_user_id,  # Different user
                    db=db_session
                )
            
            assert exc_info.value.status_code == 403
            assert "does not belong to user" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# STATUS ENDPOINT - 404 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_status_deployment_not_found():
    """
    Test status endpoint returns 404 when deployment_id does not exist.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Use non-existent deployment_id
            non_existent_deployment_id = uuid.uuid4()
            
            # Should raise 404 error
            with pytest.raises(HTTPException) as exc_info:
                await get_deployment_status(
                    deployment_id=non_existent_deployment_id,
                    user_id=user_id,
                    db=db_session
                )
            
            assert exc_info.value.status_code == 404
            assert "deployment not found" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# STATUS ENDPOINT - 403 ERRORS
# ============================================

@pytest.mark.asyncio
async def test_status_deployment_unauthorized():
    """
    Test status endpoint returns 403 when user tries to view another user's deployment.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create owner user
            owner_user_id = f"test-owner-{uuid.uuid4()}"
            owner_email = f"owner-{uuid.uuid4()}@example.com"
            
            owner_user = User(user_id=owner_user_id, email=owner_email)
            db_session.add(owner_user)
            await db_session.commit()
            
            # Create other user
            other_user_id = f"test-other-{uuid.uuid4()}"
            other_email = f"other-{uuid.uuid4()}@example.com"
            
            other_user = User(user_id=other_user_id, email=other_email)
            db_session.add(other_user)
            await db_session.commit()
            
            # Create AWS integration for owner
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
            
            # Create terraform plan for owner
            plan = TerraformPlan(
                user_id=owner_user_id,
                original_requirements="Test requirements",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=f"terraform/{owner_user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment owned by owner
            deployment = Deployment(
                user_id=owner_user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.SUCCESS
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            # Other user tries to view owner's deployment - should raise 403
            with pytest.raises(HTTPException) as exc_info:
                await get_deployment_status(
                    deployment_id=deployment.id,
                    user_id=other_user_id,  # Different user
                    db=db_session
                )
            
            assert exc_info.value.status_code == 403
            assert "does not belong to user" in exc_info.value.detail.lower()
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


# ============================================
# STATUS ENDPOINT - RESPONSE STRUCTURE
# ============================================

@pytest.mark.asyncio
async def test_status_response_structure():
    """
    Test status endpoint returns correct response structure with all required fields.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
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
            
            # Create deployment with various fields populated
            deployment = Deployment(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.SUCCESS,
                output="Terraform apply successful",
                error_message=None
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            # Get deployment status
            response = await get_deployment_status(
                deployment_id=deployment.id,
                user_id=user_id,
                db=db_session
            )
            
            # Verify all required fields are present
            assert response.id == deployment.id
            assert response.status == "success"
            assert response.output == "Terraform apply successful"
            assert response.error_message is None
            assert response.created_at is not None
            assert response.updated_at is not None
            assert response.completed_at is None  # Not set in this test
            
            # Verify field types
            assert isinstance(response.id, uuid.UUID)
            assert isinstance(response.status, str)
            assert isinstance(response.output, str) or response.output is None
            assert isinstance(response.error_message, str) or response.error_message is None
            assert isinstance(response.created_at, str)
            assert isinstance(response.updated_at, str)
            assert isinstance(response.completed_at, str) or response.completed_at is None
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_status_response_with_error():
    """
    Test status endpoint returns correct response structure for failed deployment.
    """
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a user
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
            
            # Create failed deployment with error message
            deployment = Deployment(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id,
                status=DeploymentStatus.FAILED,
                output=None,
                error_message="Terraform apply failed: Invalid configuration"
            )
            db_session.add(deployment)
            await db_session.commit()
            await db_session.refresh(deployment)
            
            # Get deployment status
            response = await get_deployment_status(
                deployment_id=deployment.id,
                user_id=user_id,
                db=db_session
            )
            
            # Verify error fields are populated correctly
            assert response.id == deployment.id
            assert response.status == "failed"
            assert response.output is None
            assert response.error_message == "Terraform apply failed: Invalid configuration"
            assert response.created_at is not None
            assert response.updated_at is not None
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()
