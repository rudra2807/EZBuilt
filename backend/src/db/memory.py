from datetime import datetime
from typing import Dict, Any

users_db: Dict[str, dict] = {}
terraform_db: Dict[str, dict] = {}
deployments_db: Dict[str, dict] = {}
connections_db: Dict[str, dict] = {}

def now_iso() -> str:
    return datetime.utcnow().isoformat()
