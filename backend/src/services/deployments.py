from datetime import datetime
import uuid
from firebase_admin import firestore
from src.utilities.firebase_client import get_firestore_client

db = get_firestore_client()

def create_deployment_record(user_id: str, terraform_id: str) -> str:
    """Create deployment record"""
    deployment_id = str(uuid.uuid4())
    doc_ref = db.collection("deployments").document(deployment_id)
    result = {
        'id': deployment_id,
        'user_id': user_id,
        'terraform_id': terraform_id,
        'status': 'started',
        'operation': 'apply',  # 'apply' or 'destroy'
        'output': '',
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None
    }
    doc_ref.set(result)
    return deployment_id

def update_deployment_status(deployment_id: str, status: str, output: str):
    """Update deployment status"""
    doc_ref = db.collection("deployments").document(deployment_id)
    snapshot = doc_ref.get()

    if not snapshot.exists:
        # Deployment record does not exist
        return

    update_data = {
        "status": status,
        "output": output
    }

    if status in ("success", "failed", "destroyed", "destroy_failed"):
        update_data["completed_at"] = datetime.utcnow().isoformat()

    doc_ref.update(update_data)

def get_deployment(deployment_id: str):
    """Get deployment record"""
    doc = db.collection("deployments").document(deployment_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()

def get_user_deployments(user_id: str) -> list[dict]:
    docs = (
        db.collection("deployments")
        .where("user_id", "==", user_id)
        .order_by("started_at")
        .stream()
    )

    return [d.to_dict() for d in docs]