import uuid
from datetime import datetime
from typing import Optional

from src.db.memory import terraform_db
from src.utilities.firebase_client import get_firestore_client

def _get_collection():
    db = get_firestore_client()
    return db.collection("terraformPlans")

def save_terraform_code(user_id: str, requirements: str, tf_code: str) -> str:
    """Save generated terraform code"""
    tf_id = str(uuid.uuid4())
    terraform_db[tf_id] = {
        'id': tf_id,
        'user_id': user_id,
        'requirements': requirements,
        'code': tf_code,
        'created_at': datetime.utcnow().isoformat()
    }
    return tf_id

def get_terraform_code(terraform_id: str):
    """Get terraform code by ID"""
    collection = _get_collection()
    doc = collection.document(terraform_id).get()
    if not doc.exists:
        return None
    return doc.to_dict().get("terraformCode")