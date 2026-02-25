import os
import subprocess

from src.utilities.schemas import ValidationResult
from src.utilities.text_utils import strip_ansi_codes

BASE_DEPLOYMENT_DIR = os.path.join(os.getcwd(), "deployments")

def validate_terraform(tf_code: str, deployment_id: str) -> ValidationResult:
    """Run terraform validation"""

    # Create the physical directory
    deployment_dir = os.path.join(BASE_DEPLOYMENT_DIR, deployment_id)
    os.makedirs(deployment_dir, exist_ok=True)

    try:
        # Write terraform code
        tf_file = os.path.join(deployment_dir, 'main.tf')
        with open(tf_file, 'w', encoding="utf-8") as f:
            f.write(tf_code)

        # terraform init
        init_result = subprocess.run(
            ['terraform', 'init'],
            cwd=deployment_dir,
            capture_output=True,
            text=True
        )
        
        if init_result.returncode != 0:
            return ValidationResult(
                valid=False,
                errors=strip_ansi_codes(init_result.stderr or init_result.stdout)
            )
        
        # terraform validate
        validate_result = subprocess.run(
            ['terraform', 'validate'],
            cwd=deployment_dir,
            capture_output=True,
            text=True
        )
        
        if validate_result.returncode != 0:
            return ValidationResult(
                valid=False,
                errors=strip_ansi_codes(validate_result.stderr or validate_result.stdout)
            )

        return ValidationResult(
            valid=True,
            errors=None
        )
    
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=f"Unexpected error during terraform validation: {e}"
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
    import shutil
    import logging
    from src.services.s3_service import download_prefix_to_tmp, S3ServiceError
    
    logger = logging.getLogger(__name__)
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
