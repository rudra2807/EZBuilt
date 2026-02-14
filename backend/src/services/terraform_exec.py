import os
import subprocess
import tempfile

from src.utilities.schemas import ValidationResult
from src.services.aws_conn import assume_role
from src.services.deployments import update_deployment_status

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
                errors=init_result.stderr or init_result.stdout
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
                errors=validate_result.stderr or validate_result.stdout
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