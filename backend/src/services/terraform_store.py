import uuid
from datetime import datetime
from typing import List, Optional

async def get_terraform_plan_from_db(terraform_id: str, db_session):
    """Get terraform plan from RDS and download files from S3"""
    from src.database.repositories import TerraformPlanRepository
    from src.services.s3_service import download_terraform_files
    import os
    
    repo = TerraformPlanRepository(db_session)
    
    try:
        plan_uuid = uuid.UUID(terraform_id)
    except ValueError:
        return None
    
    plan = await repo.get_plan(plan_uuid)
    if not plan:
        return None
    
    # Download files from S3 if s3_prefix exists
    terraform_files = {}
    if plan.s3_prefix:
        bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET")
        if bucket:
            try:
                terraform_files = download_terraform_files(bucket, plan.s3_prefix)
            except Exception as e:
                print(f"Error downloading terraform files from S3: {e}")
    
    # Return dict format compatible with existing code
    return {
        "id": str(plan.id),
        "user_id": plan.user_id,
        "requirements": plan.original_requirements,
        "structured_requirements": plan.structured_requirements,
        "terraformCode": terraform_files.get("main.tf", ""),  # Main file for backward compatibility
        "terraform_files": terraform_files,  # All files
        "s3_prefix": plan.s3_prefix,
        "validation": {
            "valid": plan.validation_passed if plan.validation_passed is not None else False,
            "errors": plan.validation_output
        },
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updatedAt": plan.updated_at.isoformat() if plan.updated_at else None,
    }

async def get_terraform_plan(terraform_id: str, db_session):
    """Get terraform code by ID from PostgreSQL"""
    return await get_terraform_plan_from_db(terraform_id, db_session)

async def get_user_terraform_plans(user_id: str, db_session) -> List[dict]:
    """Get all terraform plans for a user from PostgreSQL"""
    from src.database.repositories import TerraformPlanRepository
    
    repo = TerraformPlanRepository(db_session)
    plans = await repo.get_user_plans(user_id)
    
    # Convert to dict format for backward compatibility
    return [
        {
            'id': str(plan.id),
            'user_id': plan.user_id,
            'requirements': plan.original_requirements,
            'structured_requirements': plan.structured_requirements,
            's3_prefix': plan.s3_prefix,
            'validation': {
                'valid': plan.validation_passed if plan.validation_passed is not None else False,
                'errors': plan.validation_output
            },
            'status': plan.status,
            'created_at': plan.created_at.isoformat() if plan.created_at else None,
            'updatedAt': plan.updated_at.isoformat() if plan.updated_at else None,
        }
        for plan in plans
    ]
