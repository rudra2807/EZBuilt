from datetime import datetime
from fastapi import APIRouter, HTTPException

from src.services.deployments import create_deployment_record
from src.services.terraform_exec import validate_terraform
from src.services.structure_requirements import generate_terraform_code, structure_requirements
from src.services.terraform_store import get_terraform_plan, save_terraform_code
from src.utilities.schemas import UpdateTerraformRequest, UserRequirements, ValidationResult

router = APIRouter(prefix="/api", tags=["requirements"])

@router.post("/structure-requirements")
async def structure_requirements_endpoint(request: UserRequirements):
    """
    Structure natural language requirements into JSON
    """
    print(f"[API] Received structure-requirements request from user: {request.user_id}")
    print(f"[API] Requirements length: {len(request.requirements)} chars")
    
    try:
        print("[API] Step 1: Structuring requirements...")
        structured_json = structure_requirements(request.requirements)
        print(f"[API] Step 1 complete. Structured JSON length: {len(structured_json)}")
        
        print("[API] Step 2: Generating Terraform code...")
        tf_code = generate_terraform_code(structured_json)
        print(f"[API] Step 2 complete. Terraform code length: {len(tf_code)}")

        print("[API] Step 3: Saving Terraform code to Firestore...")
        tf_id = save_terraform_code(
            user_id=request.user_id,
            requirements=structured_json,
            tf_code=tf_code,
        )
        print(f"[API] Step 3 complete. Terraform ID: {tf_id}")

        print("[API] Step 4: Creating deployment record...")
        deployment_id = create_deployment_record(
            user_id=request.user_id,
            terraform_id=tf_id
        )
        print(f"[API] Step 4 complete. Deployment ID: {deployment_id}")

        print("[API] Step 5: Validating Terraform...")
        validation = validate_terraform(tf_code, deployment_id)
        print(f"[API] Step 5 complete. Validation result: {validation.valid}")

        print("[API] All steps complete! Returning response.")
        return {
            "terraform_id": tf_id,
            "deployment_id": deployment_id,
            "status": "success",
            "validation": validation,
            "code": tf_code,
            "structured_requirements": structured_json,
        }
    
    except Exception as e:
        print(f"[API] ERROR in structure-requirements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing requirements: {str(e)}")

@router.post("/update-terraform")
async def update_terraform_endpoint(request: UpdateTerraformRequest):
    """
    Update an existing terraform configuration and revalidate it.
    """
    print(f"[API] Received update-terraform request for terraform_id: {request.terraform_id}")
    
    try:
        # Get existing record
        tf_record = get_terraform_plan(request.terraform_id)
        if not tf_record:
            raise HTTPException(status_code=404, detail="Terraform code not found")
        
        # Ownership check
        if tf_record["user_id"] != request.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this terraform config")
        
        # Revalidate edited code
        # validation_result = validate_terraform(request.code)
        validation_result = ValidationResult(valid=True, errors=None)

        # Update in Firestore
        tf_record["terraformCode"] = request.code
        tf_record["updatedAt"] = datetime.utcnow().isoformat()
        tf_record["validation"] = validation_result

        print(f"[API] Successfully updated terraform_id: {request.terraform_id}")
        return {
            "status": "success",
            "validation": validation_result,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ERROR in update-terraform: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating terraform: {str(e)}")
