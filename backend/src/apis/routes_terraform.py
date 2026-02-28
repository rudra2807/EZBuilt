from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.database.repositories import TerraformPlanRepository, DeploymentRepository

router = APIRouter(prefix="/api", tags=["terraform"])

@router.get("/terraform/{terraform_id}")
async def get_terraform_plan_endpoint(
    terraform_id: str,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single terraform plan by id from RDS and S3.
    Optional user_id for ownership check.
    Includes the latest deployment info if available.
    """
    from src.services.terraform_store import get_terraform_plan_from_db
    from sqlalchemy import select
    from src.database.models import Deployment
    import uuid
    
    tf_record = await get_terraform_plan_from_db(terraform_id, db)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform plan not found")
    if user_id is not None and tf_record.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this plan")
    
    # Get the latest deployment for this plan
    latest_deployment = None
    try:
        plan_uuid = uuid.UUID(terraform_id)
        result = await db.execute(
            select(Deployment)
            .where(Deployment.terraform_plan_id == plan_uuid)
            .order_by(Deployment.created_at.desc())
        )
        deployment = result.scalars().first()
        
        if deployment:
            latest_deployment = {
                "id": str(deployment.id),
                "status": deployment.status.value,
                "output": deployment.output,
                "error_message": deployment.error_message,
                "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
            }
    except Exception as e:
        # If deployment lookup fails, just continue without it
        pass
    
    # Return normalized response for frontend
    return {
        "user_id": tf_record.get("user_id"),
        "terraformId": tf_record.get("id") or terraform_id,
        "requirements": tf_record.get("requirements"),
        "structured_requirements": tf_record.get("structured_requirements"),
        "terraformCode": tf_record.get("terraformCode"),  # main.tf for backward compatibility
        "terraform_files": tf_record.get("terraform_files", {}),  # All files
        "s3_prefix": tf_record.get("s3_prefix"),
        "validation": tf_record.get("validation"),
        "status": tf_record.get("status"),
        "created_at": tf_record.get("created_at"),
        "updatedAt": tf_record.get("updatedAt"),
        "latest_deployment": latest_deployment,  # NEW: Include latest deployment
    }

@router.get("/user/{user_id}/terraform")
async def get_user_terraform(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all terraform configurations for a user from PostgreSQL
    """
    repo = TerraformPlanRepository(db)
    plans = await repo.get_user_plans(user_id)
    
    # Convert to dict format for response
    terraform_configs = []
    for plan in plans:
        terraform_configs.append({
            "id": str(plan.id),
            "user_id": plan.user_id,
            "requirements": plan.original_requirements,
            "structured_requirements": plan.structured_requirements,
            "s3_prefix": plan.s3_prefix,
            "status": plan.status,
            "validation_passed": plan.validation_passed,
            "validation_output": plan.validation_output,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
        })
    
    return {"terraform_configs": terraform_configs}

@router.get("/user/{user_id}/deployments")
async def get_user_deployments_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all deployments for a user from PostgreSQL
    """
    repo = DeploymentRepository(db)
    deployments = await repo.get_user_deployments(user_id)
    
    # Convert to dict format for response
    deployment_list = []
    for deployment in deployments:
        deployment_list.append({
            "id": str(deployment.id),
            "user_id": deployment.user_id,
            "terraform_plan_id": str(deployment.terraform_plan_id),
            "aws_connection_id": str(deployment.aws_connection_id),
            "status": deployment.status.value,
            "output": deployment.output,
            "error_message": deployment.error_message,
            "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
            "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None
        })
    
    return {"deployments": deployment_list}


@router.get("/terraform/{terraform_id}/resources")
async def get_terraform_resources(
    terraform_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current state of deployed resources from PostgreSQL
    """
    from src.services.terraform_store import get_terraform_plan_from_db
    import uuid
    
    # Verify terraform plan exists
    try:
        plan_uuid = uuid.UUID(terraform_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid terraform_id format")
    
    tf_record = await get_terraform_plan_from_db(terraform_id, db)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Query deployments for this terraform plan from PostgreSQL
    from sqlalchemy import select
    from src.database.models import Deployment, DeploymentStatus
    
    result = await db.execute(
        select(Deployment)
        .where(Deployment.terraform_plan_id == plan_uuid)
        .order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()
    
    # Find successful deployments
    successful_deployments = [
        d for d in deployments 
        if d.status == DeploymentStatus.SUCCESS
    ]
    
    if not successful_deployments:
        return {
            "terraform_id": terraform_id,
            "status": "not_deployed",
            "resources": []
        }
    
    # Get the latest successful deployment
    latest_deployment = successful_deployments[0]
    
    return {
        "terraform_id": terraform_id,
        "status": "deployed",
        "deployment_id": str(latest_deployment.id),
        "deployed_at": latest_deployment.completed_at.isoformat() if latest_deployment.completed_at else None,
        "can_destroy": True
    }


@router.get("/user/{user_id}/history")
async def get_user_history(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all terraform plans with their deployments for a user
    """
    try:
        repo = TerraformPlanRepository(db)
        plans = await repo.get_user_plans_with_deployments(user_id)
        
        # Transform to response schema
        plans_data = []
        for plan in plans:
            # Calculate deployment count and latest status
            deployment_count = len(plan.deployments)
            latest_deployment_status = None
            if plan.deployments:
                # Deployments are already sorted by created_at DESC
                latest_deployment_status = plan.deployments[0].status.value
            
            # Transform deployments
            deployments_data = []
            for deployment in plan.deployments:
                deployments_data.append({
                    "id": str(deployment.id),
                    "status": deployment.status.value,
                    "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                    "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
                    "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
                    "error_message": deployment.error_message
                })
            
            plans_data.append({
                "id": str(plan.id),
                "user_id": plan.user_id,
                "original_requirements": plan.original_requirements,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "deployment_count": deployment_count,
                "latest_deployment_status": latest_deployment_status,
                "deployments": deployments_data
            })
        
        return {"plans": plans_data}
    
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error fetching user history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deployment history")

