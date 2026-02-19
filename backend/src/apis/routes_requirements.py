from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging

from src.services.deployments import create_deployment_record
from src.services.terraform_exec import validate_terraform, validate_terraform_from_s3
from src.services.structure_requirements import generate_terraform_code, structure_requirements
from src.services.terraform_store import get_terraform_plan, save_terraform_code, update_terraform_plan
from src.services.s3_service import upload_terraform_files, S3ServiceError
from src.database.connection import get_db
from src.database.repositories import TerraformPlanRepository
from src.utilities.schemas import UpdateTerraformRequest, UserRequirements, ValidationResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["requirements"])

@router.post("/structure-requirements")
async def structure_requirements_endpoint(
    request: UserRequirements,
    db: AsyncSession = Depends(get_db)
):
    """
    Structure natural language requirements into JSON, generate Terraform code,
    upload to S3, validate, and store metadata in database.
    
    Flow:
    1. Structure requirements (existing)
    2. Generate Terraform code (existing)
    3. Create DB record with status='generating'
    4. Commit to get plan_id
    5. Compute s3_prefix = f"{user_id}/{plan_id}/v1/"
    6. Upload to S3: {"main.tf": tf_code}
    7. Update plan.s3_prefix in database
    8. Validate using S3 download
    9. Update DB with validation results
    10. Set status='generated' or 'failed'
    11. Return terraform_id
    """
    print(f"[API] Received structure-requirements request from user: {request.user_id}")
    print(f"[API] Requirements length: {len(request.requirements)} chars")
    
    plan_id = None
    repo = TerraformPlanRepository(db)
    
    try:
        # Step 1: Structure requirements
        print("[API] Step 1: Structuring requirements...")
        structured_json = structure_requirements(request.requirements)
        print(f"[API] Step 1 complete. Structured JSON length: {len(structured_json)}")
        
        # Step 2: Generate Terraform code
        print("[API] Step 2: Generating Terraform code...")
        terraform_output = generate_terraform_code(structured_json)
        print(f"[API] Step 2 complete. Generated {len(terraform_output.get('files', {}))} files")
        
        # Extract files from the output
        tf_files = terraform_output.get('files', {})
        if not tf_files:
            raise HTTPException(status_code=500, detail="No Terraform files generated")
        
        # Step 3-4: Create DB record with status='generating' and commit to get plan_id
        print("[API] Step 3: Creating database record...")
        plan = await repo.create_plan(
            user_id=request.user_id,
            original_requirements=request.requirements,
            structured_requirements=structured_json,
            s3_prefix=""  # Will be set after S3 upload
        )
        plan_id = str(plan.id)
        print(f"[API] Step 3 complete. Plan ID: {plan_id}")
        
        # Step 5: Compute S3 prefix
        s3_prefix = f"{request.user_id}/{plan_id}/v1/"
        bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET")
        
        if not bucket:
            error_msg = "EZBUILT_TERRAFORM_SOURCE_BUCKET environment variable not set"
            logger.error(error_msg)
            await repo.update_plan_status(
                plan_id=plan.id,
                status='failed',
                validation_output=error_msg
            )
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 6-7: Upload to S3 and update s3_prefix
        print(f"[API] Step 4: Uploading to S3 bucket {bucket} with prefix {s3_prefix}...")
        try:
            upload_terraform_files(
                bucket=bucket,
                prefix=s3_prefix,
                files=tf_files  # Upload all generated files
            )
            print(f"[API] Step 4 complete. {len(tf_files)} files uploaded to S3")
            
            # Update s3_prefix in database
            await repo.update_plan_status(
                plan_id=plan.id,
                status='generating',
                s3_prefix=s3_prefix
            )
            print(f"[API] Updated s3_prefix in database: {s3_prefix}")
            
        except S3ServiceError as e:
            error_msg = f"S3 upload failed: {str(e)}"
            logger.error(error_msg)
            await repo.update_plan_status(
                plan_id=plan.id,
                status='failed',
                validation_output=error_msg
            )
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 8: Validate using S3 download
        print(f"[API] Step 5: Validating Terraform from S3...")
        try:
            validation = validate_terraform_from_s3(
                bucket=bucket,
                s3_prefix=s3_prefix,
                plan_id=plan_id
            )
            print(f"[API] Step 5 complete. Validation result: {validation.valid}")
            
            # Step 9-10: Update status based on validation
            await repo.update_plan_status(
                plan_id=plan.id,
                status='generated',
                validation_passed=validation.valid,
                validation_output=validation.errors
            )
            print(f"[API] Updated plan status to 'generated'")
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            logger.error(error_msg)
            await repo.update_plan_status(
                plan_id=plan.id,
                status='failed',
                validation_output=error_msg
            )
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 11: Return response
        print("[API] All steps complete! Returning response.")
        return {
            "terraform_id": plan_id,
            "status": "success",
            "validation": validation,
            "structured_requirements": structured_json,
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = f"Error processing requirements: {str(e)}"
        print(f"[API] ERROR in structure-requirements: {error_msg}")
        logger.error(error_msg)
        
        # Update database status if we have a plan_id
        if plan_id:
            try:
                await repo.update_plan_status(
                    plan_id=plan.id,
                    status='failed',
                    validation_output=error_msg
                )
            except Exception as db_error:
                logger.error(f"Failed to update plan status: {str(db_error)}")
        
        raise HTTPException(status_code=500, detail=error_msg)

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

        # Revalidate edited code (optional: pass deployment_id if you want to run validate in deployment dir)
        validation_result = validate_terraform(
            request.code, tf_record.get("deploymentId") or request.terraform_id
        )
        updated = update_terraform_plan(
            request.terraform_id,
            terraform_code=request.code,
            validation=validation_result.model_dump(),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to persist terraform update")

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
