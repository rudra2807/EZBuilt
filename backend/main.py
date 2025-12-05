# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import boto3
import subprocess
import tempfile
import os
import json
from typing import Optional
from datetime import datetime
import uuid
import firebase_admin
from firebase_admin import credentials, firestore

import structure_requirements

app = FastAPI(title="EZBuilt API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


cred = credentials.Certificate(
    os.path.join(os.path.dirname(__file__), "ezbuilt-dev-firebase-adminsdk-fbsvc-900cf233a6.json")
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Now get Firestore client from Firebase Admin
db = firestore.client()
collection = db.collection("terraformPlans")

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

class RoleArnCallback(BaseModel):
    external_id: str
    role_arn: str

class ValidationResult(BaseModel):
    valid: bool
    errors : Optional[str]

# ============================================
# IN-MEMORY DATABASE (Replace with real DB)
# ============================================

users_db = {}
terraform_db = {}
deployments_db = {}
connections_db = {}

# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_external_id(user_id: str) -> str:
    """Generate unique external ID for cross-account access"""
    return f"ezbuilt-{user_id}-{uuid.uuid4().hex[:8]}"

def save_pending_connection(user_id: str, external_id: str):
    """Save pending connection to database"""
    connections_db[external_id] = {
        'user_id': user_id,
        'external_id': external_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat()
    }

def get_user_by_external_id(external_id: str):
    """Get user by external ID"""
    return connections_db.get(external_id)

def save_role_arn(user_id: str, role_arn: str):
    """Save role ARN to user record"""
    if user_id not in users_db:
        users_db[user_id] = {}
    
    users_db[user_id]['role_arn'] = role_arn
    users_db[user_id]['connected_at'] = datetime.utcnow().isoformat()
    
    # Update connection status
    for external_id, conn in connections_db.items():
        if conn['user_id'] == user_id:
            connections_db[external_id]['status'] = 'connected'
            connections_db[external_id]['role_arn'] = role_arn

def get_user(user_id: str):
    """Get user record"""
    return users_db.get(user_id)

def assume_role(role_arn: str, external_id: str):
    """Assume role in user's AWS account"""
    sts = boto3.client('sts')
    
    try:
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='EZBuilt-Session',
            ExternalId=external_id,
            DurationSeconds=3600
        )
        return response['Credentials']
    except Exception as e:
        raise Exception(f"Failed to assume role: {str(e)}")

def call_claude_for_terraform(requirements: str) -> str:
    """
    Call Claude API to generate Terraform code
    Replace with your actual Claude integration
    """
    # TODO: Replace with actual Claude API call
    # For now, return sample terraform
    return f"""
# Generated Terraform for: {requirements}

terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "us-east-1"
}}

data "aws_ami" "amazon_linux_2" {{
  most_recent = true

  owners = ["amazon"]

  filter {{
    name   = "name"
    values = ["amzn2-ami-hvm-2.0.*-x86_64-gp2"]
  }}

  filter {{
    name   = "virtualization-type"
    values = ["hvm"]
  }}
}}

# Sample EC2 instance
resource "aws_instance" "web" {{
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = "t2.micro"

  tags = {{
    Name        = "web-server"
    ManagedBy   = "EZBuilt"
    Environment = "production"
  }}
}}

output "instance_id" {{
  value = aws_instance.web.id
}}
"""

def validate_terraform(tf_code: str) -> dict:
    """Run terraform validation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write terraform file
        tf_file = os.path.join(tmpdir, 'main.tf')
        with open(tf_file, 'w') as f:
            f.write(tf_code)
        
        # terraform init
        init_result = subprocess.run(
            ['terraform', 'init'],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if init_result.returncode != 0:
            return {
                'valid': False,
                'errors': init_result.stderr,
                'stage': 'init'
            }
        
        # terraform validate
        validate_result = subprocess.run(
            ['terraform', 'validate'],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        return {
            'valid': validate_result.returncode == 0,
            'errors': validate_result.stderr if validate_result.returncode != 0 else None,
            'stage': 'validate',
            'output': validate_result.stdout
        }

def save_terraform_code(user_id: str, requirements: str, tf_code: str) -> str:
    """Save generated terraform code"""
    tf_id = str(uuid.uuid4())
    terraform_db[tf_id] = {
        'id': tf_id,
        'user_id': user_id,
        'requirements': requirements,
        'code': tf_code,
        'created_at': datetime.utcnow().isoformat()
    }
    return tf_id

def get_terraform_code(terraform_id: str):
    """Get terraform code by ID"""
    doc = collection.document(terraform_id).get()
    if not doc.exists:
        return None
    return doc.to_dict().get("terraformCode")

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


BASE_DEPLOYMENT_DIR = os.path.join(os.getcwd(), "deployments")

def execute_terraform_apply(
    deployment_id: str,
    role_arn: str,
    external_id: str,
    tf_code: str
):
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
            ['terraform', 'plan', '-out=tfplan'],
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

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "EZBuilt API",
        "version": "1.0.0"
    }

@app.post("/api/generate-cfn-link")
async def generate_cfn_link(request: CFNLinkRequest):
    """
    Generate CloudFormation quick-create link for account connection
    """
    external_id = generate_external_id(request.user_id)
    callback_url = "https://yourplatform.com/api/cfn-callback"
    
    # CFN template URL (you need to host this on S3)
    template_url = "https://ezbuilt.s3.us-west-1.amazonaws.com/ezbuilt-cross-account-role.yaml"
    
    # Generate quick-create link
    cfn_link = (
        f"https://console.aws.amazon.com/cloudformation/home"
        f"?region=us-east-1#/stacks/quickcreate"
        f"?templateURL={template_url}"
        f"&stackName=EZBuilt-Access-{external_id[:8]}"
        f"&param_ExternalId={external_id}"
        f"&param_CallbackUrl={callback_url}"
    )
    
    # Save pending connection
    save_pending_connection(request.user_id, external_id)
    
    return {
        "cfn_link": cfn_link,
        "external_id": external_id,
        "instructions": "Click the link, review permissions, and create the CloudFormation stack"
    }

@app.post("/api/cfn-callback")
async def cfn_callback(data: RoleArnCallback):
    """
    Receives ARN from CloudFormation after stack creation
    """
    user = get_user_by_external_id(data.external_id)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid external_id")
    
    # Test role assumption
    try:
        assume_role(data.role_arn, data.external_id)
        save_role_arn(user['user_id'], data.role_arn)
        return {"status": "success", "message": "Role connected successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Role assumption failed: {str(e)}"}

@app.get("/api/connection-status/{external_id}")
async def get_connection_status(external_id: str):
    """
    Get connection status for polling
    """
    connection = connections_db.get(external_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return {
        "connected": connection['status'] == 'connected',
        "status": connection['status'],
        "role_arn": connection.get('role_arn')
    }

@app.post("/api/connect-account-manual")
async def connect_account_manual(user_id: str, role_arn: str, external_id: str):
    """
    Manual connection method (for MVP without callback)
    User provides role ARN directly
    """
    try:
        # Test assume role
        assume_role(role_arn, external_id)
        
        # Save connection
        save_role_arn(user_id, role_arn)
        
        return {
            "status": "success",
            "message": "AWS account connected successfully",
            "role_arn": role_arn
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

@app.post("/api/structure-requirements")
async def structure_requirements_endpoint(request: UserRequirements):
    """
    Structure natural language requirements into JSON
    """
    
    user_requierements = request.requirements
    structured_reqs = structure_requirements.structure_requirements(user_requierements)
    res = structure_requirements.generate_terraform_code(structured_reqs)
    print("Generated Terraform Code:")
    return res

@app.post("/api/generate-terraform")
async def generate_terraform_endpoint(request: TerraformGenerateRequest):
    """
    Generate Terraform code from natural language requirements
    """
    try:
        # Generate terraform using Claude
        tf_code = call_claude_for_terraform(request.requirements)
        
        # Validate
        validation_result = validate_terraform(tf_code)
        
        if not validation_result['valid']:
            return {
                "status": "error",
                "message": "Generated Terraform code is invalid",
                "errors": validation_result['errors']
            }
        
        # Save to database
        tf_id = save_terraform_code(request.user_id, request.requirements, tf_code)
        
        return {
            "status": "success",
            "terraform_id": tf_id,
            "code": tf_code,
            "validation": validation_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/deploy")
async def deploy_terraform_endpoint(
    request: DeployRequest,
    background_tasks: BackgroundTasks
):
    """
    Deploy terraform to user's AWS account
    """
    # Get user's role ARN
    user = get_user(request.user_id)
    if not user or 'role_arn' not in user:
        raise HTTPException(status_code=400, detail="AWS account not connected")
    
    # Get terraform code
    tf_code = get_terraform_code(request.terraform_id)
    if not tf_code:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Get external ID from connections
    external_id = None
    for ext_id, conn in connections_db.items():
        if conn['user_id'] == request.user_id and conn['status'] == 'connected':
            external_id = ext_id
            break
    
    if not external_id:
        raise HTTPException(status_code=400, detail="External ID not found")
    
    # Create deployment record
    deployment_id = create_deployment_record(request.user_id, request.terraform_id)
    
    # Run deployment in background
    background_tasks.add_task(
        execute_terraform_apply,
        deployment_id,
        user['role_arn'],
        external_id,
        tf_code
    )
    
    return {
        "deployment_id": deployment_id,
        "status": "started",
        "message": "Deployment started in background"
    }

@app.get("/api/deployment/{deployment_id}/status")
async def get_deployment_status_endpoint(deployment_id: str):
    """
    Get deployment status
    """
    deployment = get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {
        "deployment_id": deployment['id'],
        "status": deployment['status'],
        "output": deployment['output'],
        "started_at": deployment['started_at'],
        "completed_at": deployment['completed_at']
    }

@app.get("/api/user/{user_id}/terraform")
async def get_user_terraform(user_id: str):
    """
    Get all terraform configurations for a user
    """
    user_terraform = [
        tf for tf in terraform_db.values()
        if tf['user_id'] == user_id
    ]
    return {"terraform_configs": user_terraform}

@app.get("/api/user/{user_id}/deployments")
async def get_user_deployments(user_id: str):
    """
    Get all deployments for a user
    """
    user_deployments = [
        dep for dep in deployments_db.values()
        if dep['user_id'] == user_id
    ]
    return {"deployments": user_deployments}

# ============================================
# DESTROY INFRASTRUCTURE
# ============================================

class DestroyRequest(BaseModel):
    user_id: str
    terraform_id: str

def execute_terraform_destroy(
    deployment_id: str,
    role_arn: str,
    external_id: str,
    tf_code: str
):
    """Execute terraform destroy with assumed role"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write terraform code
            tf_file = os.path.join(tmpdir, 'main.tf')
            with open(tf_file, 'w') as f:
                f.write(tf_code)
            
            # Get AWS credentials via assume role
            creds = assume_role(role_arn, external_id)
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
                'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
                'AWS_SESSION_TOKEN': creds['SessionToken']
            })
            
            # terraform init
            init_result = subprocess.run(
                ['terraform', 'init'],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True
            )
            
            if init_result.returncode != 0:
                update_deployment_status(deployment_id, 'failed', f"Init failed: {init_result.stderr}")
                return
            
            # terraform destroy with auto-approve
            destroy_result = subprocess.run(
                ['terraform', 'destroy', '-auto-approve'],
                cwd=tmpdir,
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

@app.post("/api/destroy")
async def destroy_terraform_endpoint(
    request: DestroyRequest,
    background_tasks: BackgroundTasks
):
    """
    Destroy terraform infrastructure in user's AWS account
    """
    # Get user's role ARN
    user = get_user(request.user_id)
    if not user or 'role_arn' not in user:
        raise HTTPException(status_code=400, detail="AWS account not connected")
    
    # Get terraform code
    tf_record = get_terraform_code(request.terraform_id)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Get external ID from connections
    external_id = None
    for ext_id, conn in connections_db.items():
        if conn['user_id'] == request.user_id and conn['status'] == 'connected':
            external_id = ext_id
            break
    
    if not external_id:
        raise HTTPException(status_code=400, detail="External ID not found")
    
    # Create deployment record for destroy operation
    deployment_id = create_deployment_record(request.user_id, request.terraform_id)
    deployments_db[deployment_id]['operation'] = 'destroy'
    deployments_db[deployment_id]['status'] = 'destroying'
    
    # Run destroy in background
    background_tasks.add_task(
        execute_terraform_destroy,
        deployment_id,
        user['role_arn'],
        external_id,
        tf_record['code']
    )
    
    return {
        "deployment_id": deployment_id,
        "status": "destroying",
        "message": "Destroy operation started in background"
    }

@app.get("/api/terraform/{terraform_id}/resources")
async def get_terraform_resources(terraform_id: str):
    """
    Get the current state of deployed resources
    This would require implementing terraform state management
    """
    tf_record = get_terraform_code(terraform_id)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Find all deployments for this terraform
    related_deployments = [
        dep for dep in deployments_db.values()
        if dep['terraform_id'] == terraform_id
    ]
    
    # Get the latest successful deployment
    successful_deployments = [
        dep for dep in related_deployments
        if dep['status'] == 'success'
    ]
    
    if not successful_deployments:
        return {
            "terraform_id": terraform_id,
            "status": "not_deployed",
            "resources": []
        }
    
    latest_deployment = max(successful_deployments, key=lambda x: x['started_at'])
    
    return {
        "terraform_id": terraform_id,
        "status": "deployed",
        "deployment_id": latest_deployment['id'],
        "deployed_at": latest_deployment['completed_at'],
        "can_destroy": True
    }

# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    print("🚀 Starting EZBuilt API Server...")
    print("📍 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (development only)
    )