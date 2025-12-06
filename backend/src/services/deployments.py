from datetime import datetime
import uuid

from src.db.memory import deployments_db

def create_deployment_record(user_id: str, terraform_id: str) -> str:
    """Create deployment record"""
    deployment_id = str(uuid.uuid4())
    deployments_db[deployment_id] = {
        'id': deployment_id,
        'user_id': user_id,
        'terraform_id': terraform_id,
        'status': 'started',
        'operation': 'apply',  # 'apply' or 'destroy'
        'output': '',
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None
    }
    return deployment_id

def update_deployment_status(deployment_id: str, status: str, output: str):
    """Update deployment status"""
    if deployment_id in deployments_db:
        deployments_db[deployment_id]['status'] = status
        deployments_db[deployment_id]['output'] = output
        if status in ['success', 'failed']:
            deployments_db[deployment_id]['completed_at'] = datetime.utcnow().isoformat()

def get_deployment(deployment_id: str):
    """Get deployment record"""
    return deployments_db.get(deployment_id)

def get_user_deployments(user_id: str) -> list[dict]:
    return [d for d in deployments_db.values() if d["user_id"] == user_id]