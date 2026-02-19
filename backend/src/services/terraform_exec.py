import os
import subprocess
import tempfile
import re

from src.utilities.schemas import ValidationResult
from src.services.aws_conn import assume_role
from src.services.deployments import update_deployment_status

BASE_DEPLOYMENT_DIR = os.path.join(os.getcwd(), "deployments")


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

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

def execute_terraform_apply(
    deployment_id: str,
    role_arn: str,
    external_id: str,
    tf_code: str
):
    print("Executing terraform apply...")
    """Execute terraform apply in a persistent directory"""
    try:
        # Create the physical directory
        deployment_dir = os.path.join(BASE_DEPLOYMENT_DIR, deployment_id)
        os.makedirs(deployment_dir, exist_ok=True)

        # Write terraform code
        tf_file = os.path.join(deployment_dir, 'main.tf')
        with open(tf_file, 'w') as f:
            f.write(tf_code)

        # Assume role
        creds = assume_role(role_arn, external_id)

        # Set environment
        env = os.environ.copy()
        env.update({
            'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
            'AWS_SESSION_TOKEN': creds['SessionToken']
        })

        # terraform init
        init_result = subprocess.run(
            ['terraform', 'init'],
            cwd=deployment_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if init_result.returncode != 0:
            update_deployment_status(deployment_id, 'failed', f"Init failed: {init_result.stderr}")
            return

        # terraform plan
        plan_result = subprocess.run(
            ['terraform', 'plan', '-out=tfplan', '-no-color', '-input=false'],
            cwd=deployment_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if plan_result.returncode != 0:
            update_deployment_status(deployment_id, 'failed', f"Plan failed: {plan_result.stderr}")
            return

        update_deployment_status(deployment_id, 'planned', plan_result.stdout)

        # terraform apply
        apply_result = subprocess.run(
            ['terraform', 'apply', '-auto-approve', 'tfplan'],
            cwd=deployment_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if apply_result.returncode == 0:
            update_deployment_status(deployment_id, 'success', apply_result.stdout)
        else:
            update_deployment_status(deployment_id, 'failed', apply_result.stderr)

    except Exception as e:
        update_deployment_status(deployment_id, 'failed', f"Error: {str(e)}")

def execute_terraform_destroy(
    deployment_id: str,
    role_arn: str,
    external_id: str,
    tf_code: str
):
    """Execute terraform destroy with assumed role"""
    try:
        deployment_dir = os.path.join(BASE_DEPLOYMENT_DIR, deployment_id)
        # tf_file = os.path.join(deployment_dir, 'main.tf')
        print("destroying deployment_dir: " + deployment_dir)
        creds = assume_role(role_arn, external_id)
        
        # Set environment variables
        env = os.environ.copy()
        env.update({
            'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
            'AWS_SESSION_TOKEN': creds['SessionToken']
        })
        
        # # terraform init
        # init_result = subprocess.run(
        #     ['terraform', 'init'],
        #     cwd=deployment_dir,
        #     env=env,
        #     capture_output=True,
        #     text=True
        # )
        
        # if init_result.returncode != 0:
        #     update_deployment_status(deployment_id, 'failed', f"Init failed: {init_result.stderr}")
        #     return
        
        # terraform destroy with auto-approve
        destroy_result = subprocess.run(
            ['terraform', 'destroy', '-auto-approve', '-no-color', '-input=false'],
            cwd=deployment_dir,
            env=env,
            capture_output=True,
            text=True
        )
        
        if destroy_result.returncode == 0:
            update_deployment_status(deployment_id, 'destroyed', destroy_result.stdout)
        else:
            update_deployment_status(deployment_id, 'destroy_failed', destroy_result.stderr)
    
    except Exception as e:
        update_deployment_status(deployment_id, 'destroy_failed', f"Error: {str(e)}")


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
