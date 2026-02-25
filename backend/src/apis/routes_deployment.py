"""
Deployment API Endpoints

This module provides REST API endpoints for managing Terraform deployments:
- POST /api/deploy: Trigger Terraform apply operation
- POST /api/destroy: Trigger Terraform destroy operation
- GET /api/deployment/{id}/status: Get deployment status

All endpoints enforce user isolation through JWT-based authentication.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid
from datetime import datetime

from src.database.connection import get_db
from src.database.repositories import (
    DeploymentRepository,
    TerraformPlanRepository,
    AWSIntegrationRepository
)
from src.database.models import DeploymentStatus, IntegrationStatus
from src.services.deployment_service import execute_terraform_apply, execute_terraform_destroy

router = APIRouter(prefix="/api", tags=["deployment"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class DeployRequest(BaseModel):
    """Request model for deploying Terraform infrastructure"""
    user_id: str  # Temporary: until JWT auth is implemented
    terraform_plan_id: uuid.UUID
    aws_connection_id: uuid.UUID


class DestroyRequest(BaseModel):
    """Request model for destroying Terraform infrastructure"""
    user_id: str  # Temporary: until JWT auth is implemented
    deployment_id: uuid.UUID


class DeploymentResponse(BaseModel):
    """Response model for deployment status"""
    id: uuid.UUID
    status: str
    output: str | None
    error_message: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


# ============================================
# DEPENDENCIES
# ============================================

async def get_current_user_id() -> str:
    """
    Extract user_id from JWT token.
    
    TODO: Implement JWT token validation and extraction.
    This is a placeholder that should be replaced with actual JWT middleware
    that validates the token and extracts the user_id (Cognito sub).
    
    Expected implementation:
    1. Extract Authorization header
    2. Validate JWT token signature
    3. Extract 'sub' claim from token
    4. Return user_id
    
    Raises:
        HTTPException: 501 Not Implemented (placeholder)
    
    Returns:
        str: User ID from JWT token
    """
    # This will be implemented with proper JWT middleware
    # For now, raise an error to indicate it needs implementation
    raise HTTPException(
        status_code=501,
        detail="JWT authentication not yet implemented"
    )


# ============================================
# ENDPOINTS
# ============================================

@router.post("/deploy", status_code=202)
async def deploy(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Trigger Terraform deployment.
    
    Temporary: Accepts user_id in request body until JWT auth is implemented.
    
    Flow:
    1. Get user_id from request body (temporary workaround)
    2. Validate terraform_plan ownership and existence
    3. Validate aws_connection ownership, existence, and status
    4. Create deployment record with status STARTED
    5. Enqueue background task for Terraform execution
    6. Return deployment_id with 202 Accepted
    
    Args:
        request: Deploy request with user_id, terraform_plan_id and aws_connection_id
        background_tasks: FastAPI background tasks manager
        db: Database session (dependency)
    
    Returns:
        dict: Response with deployment_id, status, and message
    
    Raises:
        HTTPException 404: Terraform plan or AWS connection not found
        HTTPException 400: AWS connection not in connected status
    
    Validates Requirements:
        2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10
    """
    # Temporary: Get user_id from request body
    user_id = request.user_id
    
    # Validate terraform_plan ownership
    plan_repo = TerraformPlanRepository(db)
    plan = await plan_repo.get_plan(request.terraform_plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Terraform plan not found"
        )
    
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Terraform plan not found or does not belong to user"
        )
    
    # Validate aws_connection ownership and status
    aws_repo = AWSIntegrationRepository(db)
    aws_conn = await aws_repo.get_by_external_id(str(request.aws_connection_id))
    
    # Try to get by ID if external_id lookup fails
    if not aws_conn:
        # Query by ID directly
        from sqlalchemy import select
        from src.database.models import AWSIntegration
        result = await db.execute(
            select(AWSIntegration).where(AWSIntegration.id == request.aws_connection_id)
        )
        aws_conn = result.scalar_one_or_none()
    
    if not aws_conn:
        raise HTTPException(
            status_code=404,
            detail="AWS connection not found"
        )
    
    if aws_conn.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="AWS connection not found or does not belong to user"
        )
    
    if aws_conn.status != IntegrationStatus.CONNECTED:
        raise HTTPException(
            status_code=400,
            detail=f"AWS connection status is {aws_conn.status.value}, must be connected"
        )
    
    # Create deployment record
    deployment_repo = DeploymentRepository(db)
    deployment = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=request.terraform_plan_id,
        aws_connection_id=request.aws_connection_id
    )
    
    # Enqueue background task
    background_tasks.add_task(
        execute_terraform_apply,
        deployment_id=deployment.id,
        terraform_plan_id=plan.id,
        s3_prefix=plan.s3_prefix,
        role_arn=aws_conn.role_arn,
        external_id=aws_conn.external_id,
        db=db
    )
    
    return {
        "deployment_id": str(deployment.id),
        "status": "started",
        "message": "Deployment started in background"
    }


@router.post("/destroy", status_code=202)
async def destroy(
    request: DestroyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Trigger Terraform destroy operation.
    
    Temporary: Accepts user_id in request body until JWT auth is implemented.
    
    Flow:
    1. Get user_id from request body (temporary workaround)
    2. Validate deployment ownership and existence
    3. Validate deployment status is SUCCESS
    4. Update deployment status to STARTED
    5. Enqueue background task for Terraform destroy
    6. Return 202 Accepted
    
    Args:
        request: Destroy request with user_id and deployment_id
        background_tasks: FastAPI background tasks manager
        db: Database session (dependency)
    
    Returns:
        dict: Response with deployment_id, status, and message
    
    Raises:
        HTTPException 404: Deployment not found
        HTTPException 403: Deployment does not belong to user
        HTTPException 400: Deployment status is not SUCCESS
    
    Validates Requirements:
        3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
    """
    # Temporary: Get user_id from request body
    user_id = request.user_id
    
    # Validate deployment ownership
    deployment_repo = DeploymentRepository(db)
    deployment = await deployment_repo.get_by_id(request.deployment_id, user_id)
    
    if not deployment:
        # Check if deployment exists at all (for proper error message)
        from sqlalchemy import select
        from src.database.models import Deployment
        result = await db.execute(
            select(Deployment).where(Deployment.id == request.deployment_id)
        )
        exists = result.scalar_one_or_none()
        
        if exists:
            raise HTTPException(
                status_code=403,
                detail="Deployment not found or does not belong to user"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Deployment not found"
            )
    
    if deployment.status != DeploymentStatus.SUCCESS:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot destroy deployment with status {deployment.status.value}, must be success"
        )
    
    # Update status to STARTED
    await deployment_repo.update_status(request.deployment_id, DeploymentStatus.STARTED)
    
    # Get AWS connection details
    from sqlalchemy import select
    from src.database.models import AWSIntegration
    result = await db.execute(
        select(AWSIntegration).where(AWSIntegration.id == deployment.aws_connection_id)
    )
    aws_conn = result.scalar_one_or_none()
    
    if not aws_conn:
        raise HTTPException(
            status_code=400,
            detail="AWS connection not found for this deployment"
        )
    
    # Enqueue background task
    background_tasks.add_task(
        execute_terraform_destroy,
        deployment_id=deployment.id,
        role_arn=aws_conn.role_arn,
        external_id=aws_conn.external_id,
        db=db
    )
    
    return {
        "deployment_id": str(deployment.id),
        "status": "started",
        "message": "Destroy started in background"
    }


@router.get("/deployment/{deployment_id}/status")
async def get_deployment_status(
    deployment_id: uuid.UUID,
    user_id: str,  # Temporary: from query param until JWT auth is implemented
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """
    Get deployment status and details.
    
    Flow:
    1. Extract user_id from JWT token
    2. Validate deployment ownership and existence
    3. Return deployment details
    
    Args:
        deployment_id: UUID of the deployment
        user_id: User ID extracted from JWT token (dependency)
        db: Database session (dependency)
    
    Returns:
        DeploymentResponse: Deployment details including status, output, and timestamps
    
    Raises:
        HTTPException 404: Deployment not found
        HTTPException 403: Deployment does not belong to user
    
    Validates Requirements:
        4.1, 4.2, 4.3, 4.4, 4.5
    """
    deployment_repo = DeploymentRepository(db)
    deployment = await deployment_repo.get_by_id(deployment_id, user_id)
    
    if not deployment:
        # Check if deployment exists at all (for proper error message)
        from sqlalchemy import select
        from src.database.models import Deployment
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        exists = result.scalar_one_or_none()
        
        if exists:
            raise HTTPException(
                status_code=403,
                detail="Deployment not found or does not belong to user"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Deployment not found"
            )
    
    return DeploymentResponse(
        id=deployment.id,
        status=deployment.status.value,
        output=deployment.output,
        error_message=deployment.error_message,
        created_at=deployment.created_at.isoformat(),
        updated_at=deployment.updated_at.isoformat(),
        completed_at=deployment.completed_at.isoformat() if deployment.completed_at else None
    )
