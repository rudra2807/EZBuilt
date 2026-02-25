"""
Deployment Service Layer for Terraform Execution

This module provides functions for executing Terraform apply and destroy operations
in background tasks, with S3 file downloads, AWS role assumption, and status tracking.
Also includes Terraform validation utilities.
"""

import os
import logging
import uuid
import shutil
import subprocess
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import DeploymentStatus
from src.database.repositories import DeploymentRepository
from src.services.s3_service import download_prefix_to_tmp, S3ServiceError
from src.services.aws_conn import assume_role
from src.utilities.schemas import ValidationResult
from src.utilities.text_utils import strip_ansi_codes

# Configure logging
logger = logging.getLogger(__name__)


async def execute_terraform_apply(
    deployment_id: uuid.UUID,
    terraform_plan_id: uuid.UUID,
    s3_prefix: str,
    role_arn: str,
    external_id: str,
    db: AsyncSession
):
    """
    Execute Terraform apply in background task.
    
    Flow:
    1. Update status to RUNNING
    2. Download files from S3 to /tmp/{deployment_id}/
    3. Assume AWS role
    4. Run terraform init
    5. Run terraform plan
    6. Run terraform apply
    7. Update status to SUCCESS or FAILED
    8. Cleanup temp directory
    
    Args:
        deployment_id: UUID of the deployment record
        terraform_plan_id: UUID of the terraform plan
        s3_prefix: S3 prefix containing Terraform files
        role_arn: AWS IAM role ARN to assume
        external_id: External ID for role assumption
        db: Database session
    """
    repo = DeploymentRepository(db)
    import tempfile
    import platform
    
    # Use platform-appropriate temp directory
    if platform.system() == 'Windows':
        tmp_base = tempfile.gettempdir()
    else:
        tmp_base = "/tmp"
    
    tmp_dir = os.path.join(tmp_base, str(deployment_id))
    bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET") or os.environ.get("TERRAFORM_SOURCE_BUCKET")
    
    if not bucket:
        error_msg = "EZBUILT_TERRAFORM_SOURCE_BUCKET environment variable not set"
        logger.error(error_msg, extra={"deployment_id": str(deployment_id)})
        await repo.update_status(
            deployment_id,
            DeploymentStatus.FAILED,
            error_message=error_msg
        )
        return

    try:
        logger.info(
            f"Starting deployment {deployment_id} for plan {terraform_plan_id}",
            extra={
                "deployment_id": str(deployment_id),
                "terraform_plan_id": str(terraform_plan_id)
            }
        )

        # Update status to RUNNING
        await repo.update_status(deployment_id, DeploymentStatus.RUNNING)

        # Download files from S3
        logger.info(
            f"Downloading files from s3://{bucket}/{s3_prefix}",
            extra={
                "bucket": bucket,
                "prefix": s3_prefix,
                "deployment_id": str(deployment_id)
            }
        )
        try:
            downloaded_files = download_prefix_to_tmp(bucket, s3_prefix, tmp_dir)
            logger.info(
                f"Downloaded {len(downloaded_files)} files to {tmp_dir}",
                extra={
                    "file_count": len(downloaded_files),
                    "tmp_dir": tmp_dir,
                    "deployment_id": str(deployment_id)
                }
            )
        except S3ServiceError as e:
            logger.error(
                f"S3 download failed: {str(e)}",
                extra={"deployment_id": str(deployment_id), "error": str(e)}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.FAILED,
                error_message=f"S3 download failed: {str(e)}"
            )
            return

        # Assume AWS role
        logger.info(
            f"Assuming role {role_arn}",
            extra={
                "role_arn": role_arn,
                "deployment_id": str(deployment_id)
            }
        )
        creds = assume_role(role_arn, external_id)

        # Set environment variables
        env = os.environ.copy()
        env.update({
            'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
            'AWS_SESSION_TOKEN': creds['SessionToken']
        })

        # Terraform init
        logger.info(
            f"Running terraform init in {tmp_dir}",
            extra={
                "command": "terraform init",
                "working_directory": tmp_dir,
                "deployment_id": str(deployment_id)
            }
        )
        init_result = subprocess.run(
            ['terraform', 'init'],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if init_result.returncode != 0:
            error = strip_ansi_codes(init_result.stderr or init_result.stdout)
            logger.error(
                f"Terraform init failed: {error}",
                extra={"deployment_id": str(deployment_id), "error": error}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.FAILED,
                error_message=f"Init failed: {error}"
            )
            return

        # Terraform plan
        logger.info(
            f"Running terraform plan in {tmp_dir}",
            extra={
                "command": "terraform plan",
                "working_directory": tmp_dir,
                "deployment_id": str(deployment_id)
            }
        )
        plan_result = subprocess.run(
            ['terraform', 'plan', '-out=tfplan', '-no-color', '-input=false'],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if plan_result.returncode != 0:
            error = strip_ansi_codes(plan_result.stderr or plan_result.stdout)
            logger.error(
                f"Terraform plan failed: {error}",
                extra={"deployment_id": str(deployment_id), "error": error}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.FAILED,
                error_message=f"Plan failed: {error}"
            )
            return

        # Terraform apply
        logger.info(
            f"Running terraform apply in {tmp_dir}",
            extra={
                "command": "terraform apply",
                "working_directory": tmp_dir,
                "deployment_id": str(deployment_id)
            }
        )
        apply_result = subprocess.run(
            ['terraform', 'apply', '-auto-approve', 'tfplan'],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if apply_result.returncode == 0:
            output = strip_ansi_codes(apply_result.stdout)
            logger.info(
                f"Terraform apply succeeded for deployment {deployment_id}",
                extra={
                    "deployment_id": str(deployment_id),
                    "status": "success"
                }
            )
            
            # Upload terraform.tfstate to S3 for future destroy operations
            tfstate_path = os.path.join(tmp_dir, "terraform.tfstate")
            if os.path.exists(tfstate_path):
                try:
                    logger.info(
                        f"Uploading terraform.tfstate to S3",
                        extra={
                            "deployment_id": str(deployment_id),
                            "s3_prefix": s3_prefix
                        }
                    )
                    with open(tfstate_path, 'r') as f:
                        tfstate_content = f.read()
                    
                    from src.services.s3_service import upload_terraform_files
                    upload_terraform_files(
                        bucket=bucket,
                        prefix=s3_prefix,
                        files={"terraform.tfstate": tfstate_content}
                    )
                    logger.info(
                        f"Successfully uploaded terraform.tfstate",
                        extra={"deployment_id": str(deployment_id)}
                    )
                except Exception as state_upload_error:
                    logger.error(
                        f"Failed to upload terraform.tfstate: {str(state_upload_error)}",
                        extra={
                            "deployment_id": str(deployment_id),
                            "error": str(state_upload_error)
                        }
                    )
                    # Don't fail the deployment if state upload fails
                    # The deployment was successful, we just couldn't save the state
            
            await repo.update_status(
                deployment_id,
                DeploymentStatus.SUCCESS,
                output=output
            )
        else:
            error = strip_ansi_codes(apply_result.stderr or apply_result.stdout)
            logger.error(
                f"Terraform apply failed: {error}",
                extra={"deployment_id": str(deployment_id), "error": error}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.FAILED,
                error_message=f"Apply failed: {error}"
            )

    except Exception as e:
        logger.error(
            f"Unexpected error in deployment {deployment_id}: {str(e)}",
            extra={"deployment_id": str(deployment_id), "error": str(e)},
            exc_info=True
        )
        await repo.update_status(
            deployment_id,
            DeploymentStatus.FAILED,
            error_message=f"Unexpected error: {str(e)}"
        )

    finally:
        # Cleanup temp directory
        if os.path.exists(tmp_dir):
            logger.info(
                f"Cleaning up {tmp_dir}",
                extra={
                    "tmp_dir": tmp_dir,
                    "deployment_id": str(deployment_id)
                }
            )
            try:
                shutil.rmtree(tmp_dir)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup {tmp_dir}: {str(cleanup_error)}",
                    extra={
                        "tmp_dir": tmp_dir,
                        "deployment_id": str(deployment_id),
                        "error": str(cleanup_error)
                    }
                )


async def execute_terraform_destroy(
    deployment_id: uuid.UUID,
    role_arn: str,
    external_id: str,
    db: AsyncSession
):
    """
    Execute Terraform destroy in background task.
    
    Flow:
    1. Update status to RUNNING
    2. Get deployment details to find terraform_plan_id and s3_prefix
    3. Download Terraform files from S3 to temp directory
    4. Assume AWS role
    5. Run terraform init
    6. Run terraform destroy
    7. Update status to DESTROYED or DESTROY_FAILED
    8. Cleanup temp directory
    
    Args:
        deployment_id: UUID of the deployment record
        role_arn: AWS IAM role ARN to assume
        external_id: External ID for role assumption
        db: Database session
    """
    repo = DeploymentRepository(db)
    import tempfile
    import platform
    
    # Use platform-appropriate temp directory
    if platform.system() == 'Windows':
        tmp_base = tempfile.gettempdir()
    else:
        tmp_base = "/tmp"
    
    tmp_dir = os.path.join(tmp_base, str(deployment_id))
    bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET") or os.environ.get("TERRAFORM_SOURCE_BUCKET")

    try:
        logger.info(
            f"Starting destroy for deployment {deployment_id}",
            extra={"deployment_id": str(deployment_id)}
        )

        # Update status to RUNNING
        await repo.update_status(deployment_id, DeploymentStatus.RUNNING)
        
        # Get deployment to find terraform_plan_id
        from sqlalchemy import select
        from src.database.models import Deployment, TerraformPlan
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise Exception("Deployment not found")
        
        # Get terraform plan to find s3_prefix
        result = await db.execute(
            select(TerraformPlan).where(TerraformPlan.id == deployment.terraform_plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan or not plan.s3_prefix:
            raise Exception("Terraform plan or S3 prefix not found")
        
        if not bucket:
            raise Exception("EZBUILT_TERRAFORM_SOURCE_BUCKET environment variable not set")
        
        # Download files from S3
        logger.info(
            f"Downloading files from s3://{bucket}/{plan.s3_prefix}",
            extra={
                "bucket": bucket,
                "prefix": plan.s3_prefix,
                "deployment_id": str(deployment_id)
            }
        )
        try:
            downloaded_files = download_prefix_to_tmp(bucket, plan.s3_prefix, tmp_dir)
            logger.info(
                f"Downloaded {len(downloaded_files)} files to {tmp_dir}",
                extra={
                    "file_count": len(downloaded_files),
                    "tmp_dir": tmp_dir,
                    "deployment_id": str(deployment_id)
                }
            )
        except S3ServiceError as e:
            logger.error(
                f"S3 download failed: {str(e)}",
                extra={"deployment_id": str(deployment_id), "error": str(e)}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.DESTROY_FAILED,
                error_message=f"S3 download failed: {str(e)}"
            )
            return

        # Assume AWS role
        logger.info(
            f"Assuming role {role_arn}",
            extra={
                "role_arn": role_arn,
                "deployment_id": str(deployment_id)
            }
        )
        creds = assume_role(role_arn, external_id)

        # Set environment variables
        env = os.environ.copy()
        env.update({
            'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
            'AWS_SESSION_TOKEN': creds['SessionToken']
        })
        
        # Terraform init
        logger.info(
            f"Running terraform init in {tmp_dir}",
            extra={
                "command": "terraform init",
                "working_directory": tmp_dir,
                "deployment_id": str(deployment_id)
            }
        )
        init_result = subprocess.run(
            ['terraform', 'init'],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if init_result.returncode != 0:
            error = strip_ansi_codes(init_result.stderr or init_result.stdout)
            logger.error(
                f"Terraform init failed: {error}",
                extra={"deployment_id": str(deployment_id), "error": error}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.DESTROY_FAILED,
                error_message=f"Init failed: {error}"
            )
            return

        # Terraform destroy
        logger.info(
            f"Running terraform destroy in {tmp_dir}",
            extra={
                "command": "terraform destroy",
                "working_directory": tmp_dir,
                "deployment_id": str(deployment_id)
            }
        )
        destroy_result = subprocess.run(
            ['terraform', 'destroy', '-auto-approve', '-no-color', '-input=false'],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if destroy_result.returncode == 0:
            output = strip_ansi_codes(destroy_result.stdout)
            logger.info(
                f"Terraform destroy succeeded for deployment {deployment_id}",
                extra={
                    "deployment_id": str(deployment_id),
                    "status": "destroyed"
                }
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.DESTROYED,
                output=output
            )
        else:
            error = strip_ansi_codes(destroy_result.stderr or destroy_result.stdout)
            logger.error(
                f"Terraform destroy failed: {error}",
                extra={"deployment_id": str(deployment_id), "error": error}
            )
            await repo.update_status(
                deployment_id,
                DeploymentStatus.DESTROY_FAILED,
                error_message=f"Destroy failed: {error}"
            )

    except Exception as e:
        logger.error(
            f"Unexpected error in destroy {deployment_id}: {str(e)}",
            extra={"deployment_id": str(deployment_id), "error": str(e)},
            exc_info=True
        )
        await repo.update_status(
            deployment_id,
            DeploymentStatus.DESTROY_FAILED,
            error_message=f"Unexpected error: {str(e)}"
        )

    finally:
        # Cleanup temp directory
        if os.path.exists(tmp_dir):
            logger.info(
                f"Cleaning up {tmp_dir}",
                extra={
                    "tmp_dir": tmp_dir,
                    "deployment_id": str(deployment_id)
                }
            )
            try:
                shutil.rmtree(tmp_dir)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup {tmp_dir}: {str(cleanup_error)}",
                    extra={
                        "tmp_dir": tmp_dir,
                        "deployment_id": str(deployment_id),
                        "error": str(cleanup_error)
                    }
                )


def validate_terraform_from_s3(
    bucket: str,
    s3_prefix: str,
    plan_id: str
) -> ValidationResult:
    """
    Validate Terraform code by downloading from S3 to isolated /tmp directory.
    
    Flow:
    1. Create isolated /tmp/{plan_id}/ directory
    2. Download files from S3 using download_prefix_to_tmp()
    3. Run terraform init -backend=false
    4. Run terraform validate
    5. Clean up /tmp directory (in finally block)
    6. Return validation result
    
    Args:
        bucket: S3 bucket name
        s3_prefix: S3 prefix to download from (e.g., "user123/plan456/v1/")
        plan_id: Unique plan ID for creating isolated tmp directory
    
    Returns:
        ValidationResult with valid flag and error messages
    
    Note:
        The /tmp directory is always cleaned up, even if validation fails.
    """
    tmp_dir = f"/tmp/{plan_id}"
    
    try:
        # Ensure clean directory (remove if exists)
        if os.path.exists(tmp_dir):
            logger.info(f"Removing existing directory: {tmp_dir}")
            shutil.rmtree(tmp_dir)
        
        # Download files from S3
        logger.info(f"Downloading files from s3://{bucket}/{s3_prefix} to {tmp_dir}")
        try:
            downloaded_files = download_prefix_to_tmp(bucket, s3_prefix, tmp_dir)
            logger.info(f"Downloaded {len(downloaded_files)} files")
        except S3ServiceError as e:
            logger.error(f"S3 download failed: {str(e)}")
            return ValidationResult(
                valid=False,
                errors=f"Failed to download files from S3: {str(e)}"
            )
        
        # Run terraform init -backend=false
        logger.info(f"Running terraform init in {tmp_dir}")
        init_result = subprocess.run(
            ['terraform', 'init', '-backend=false'],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )
        
        if init_result.returncode != 0:
            logger.error(f"Terraform init failed: {init_result.stderr}")
            return ValidationResult(
                valid=False,
                errors=strip_ansi_codes(init_result.stderr or init_result.stdout)
            )
        
        # Run terraform validate
        logger.info(f"Running terraform validate in {tmp_dir}")
        validate_result = subprocess.run(
            ['terraform', 'validate'],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )
        
        if validate_result.returncode != 0:
            logger.error(f"Terraform validate failed: {validate_result.stderr}")
            return ValidationResult(
                valid=False,
                errors=strip_ansi_codes(validate_result.stderr or validate_result.stdout)
            )
        
        logger.info("Terraform validation successful")
        return ValidationResult(valid=True, errors=None)
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return ValidationResult(
            valid=False,
            errors=f"Validation error: {str(e)}"
        )
    finally:
        # Always clean up tmp directory
        if os.path.exists(tmp_dir):
            logger.info(f"Cleaning up {tmp_dir}")
            try:
                shutil.rmtree(tmp_dir)
                logger.info(f"Successfully cleaned up {tmp_dir}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up {tmp_dir}: {str(cleanup_error)}")
