import uuid
from datetime import datetime
from typing import List, Optional

from src.utilities.firebase_client import get_firestore_client

def _get_collection():
    db = get_firestore_client()
    return db.collection("terraformPlans")

def save_terraform_code(user_id: str, requirements: str, tf_code: str) -> str:
    """Save generated terraform code to Firestore"""
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

def get_terraform_plan(terraform_id: str):
    """Get terraform code by ID from Firestore"""
    collection = _get_collection()
    doc = collection.document(terraform_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()

def get_user_terraform_plans(user_id: str) -> List[dict]:
    """Get all terraform plans for a user from Firestore"""
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
    """Update an existing terraform plan. Only provided fields are updated."""
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
