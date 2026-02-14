from typing import Optional
from pydantic import BaseModel

# ============================================
# MODELS
# ============================================

class CFNLinkRequest(BaseModel):
    user_id: str

class UserRequirements(BaseModel):
    user_id: str
    requirements: str

class TerraformGenerateRequest(BaseModel):
    user_id: str
    requirements: str

class DeployRequest(BaseModel):
    user_id: str
    terraform_id: str
    deployment_id: str

class RoleArnCallback(BaseModel):
    external_id: str
    role_arn: str

class UpdateTerraformRequest(BaseModel):
    user_id: str
    terraform_id: str
    code: str

class ValidationResult(BaseModel):
    valid: bool
    errors : Optional[str] = None

class DestroyRequest(BaseModel):
    user_id: str
    terraform_id: str
    deployment_id: str