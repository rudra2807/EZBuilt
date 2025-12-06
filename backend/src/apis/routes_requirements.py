from fastapi import APIRouter

from src.services.structure_requirements import generate_terraform_code, structure_requirements
from src.services.terraform_store import save_terraform_code
from src.utilities.schemas import UserRequirements, ValidationResult

router = APIRouter(prefix="/api", tags=["requirements"])

@router.post("/structure-requirements")
async def structure_requirements_endpoint(request: UserRequirements):
    """
    Structure natural language requirements into JSON
    """
    
    structured_json = structure_requirements(request.requirements)
    
    tf_code = generate_terraform_code(structured_json)

    tf_id = save_terraform_code(
            user_id=request.user_id,          # add user_id to your schema if needed
            requirements=structured_json,
            tf_code=tf_code,
        )


    # TODO: Run terraform validate here using your validate_terraform service
    validation = ValidationResult(valid=True, errors=None)

    return {
        "terraform_id": tf_id,
        "status": "success",
        "validation": validation,
        "code": tf_code,
        "structured_requirements": structured_json,
    }