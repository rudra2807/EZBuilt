import uuid
from datetime import datetime
from typing import List, Optional

from src.utilities.firebase_client import get_firestore_client

def _get_collection():
    db = get_firestore_client()
    return db.collection("terraformPlans")

def save_terraform_code(user_id: str, requirements: str, tf_code: str) -> str:
    """Save generated terraform code to Firestore (DEPRECATED - use RDS)"""
    tf_id = str(uuid.uuid4())
    collection = _get_collection()
    doc_ref = collection.document(tf_id)
    doc_ref.set({
        'id': tf_id,
        'user_id': user_id,
        'requirements': requirements,
        'terraformCode': tf_code,
        'created_at': datetime.utcnow().isoformat()
    })
    return tf_id

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

def get_terraform_plan(terraform_id: str):
    """Get terraform code by ID from Firestore (DEPRECATED - use get_terraform_plan_from_db)"""
    collection = _get_collection()
    doc = collection.document(terraform_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()

def get_user_terraform_plans(user_id: str) -> List[dict]:
    """Get all terraform plans for a user from Firestore (DEPRECATED - use RDS)"""
    collection = _get_collection()
    docs = collection.where("user_id", "==", user_id).stream()
    return [doc.to_dict() for doc in docs]


def update_terraform_plan(
    terraform_id: str,
    *,
    terraform_code: Optional[str] = None,
    requirements: Optional[str] = None,
    deployment_id: Optional[str] = None,
    validation: Optional[dict] = None,
) -> bool:
    """Update an existing terraform plan in Firestore (DEPRECATED - use RDS)"""
    collection = _get_collection()
    doc_ref = collection.document(terraform_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    update_data = {"updatedAt": datetime.utcnow().isoformat()}
    if terraform_code is not None:
        update_data["terraformCode"] = terraform_code
    if requirements is not None:
        update_data["requirements"] = requirements
    if deployment_id is not None:
        update_data["deploymentId"] = deployment_id
    if validation is not None:
        update_data["validation"] = validation
    doc_ref.update(update_data)
    return True
