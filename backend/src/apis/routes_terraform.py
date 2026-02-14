from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.services.aws_conn import get_user
from src.services.deployments import create_deployment_record, get_deployment, get_user_deployments
from src.services.terraform_exec import execute_terraform_apply, execute_terraform_destroy
from src.services.terraform_store import get_terraform_plan, get_user_terraform_plans
from src.utilities.schemas import DeployRequest, DestroyRequest
from src.utilities.firebase_client import get_firestore_client

router = APIRouter(prefix="/api", tags=["terraform"])
db = get_firestore_client()

@router.post("/deploy")
async def deploy_terraform_endpoint(
    request: DeployRequest,
    background_tasks: BackgroundTasks
):
    """
    Deploy terraform to user's AWS account
    """
    # Get user's role ARN
    user = get_user(request.user_id)
    print("User fetched for deployment:", user)
    if not user or 'roleArn' not in user:
        raise HTTPException(status_code=400, detail="AWS account not connected")
    
    # Get terraform code
    tf_record = get_terraform_plan(request.terraform_id)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Get external ID
    external_id = user.get("externalId")
    if not external_id:
        raise HTTPException(status_code=400, detail="External ID not found")
    
    # Run deployment in background
    background_tasks.add_task(
        execute_terraform_apply,
        request.deployment_id,
        user['roleArn'],
        external_id,
        tf_record["terraformCode"]
    )
    
    return {
        "deployment_id": tf_record["deploymentId"],
        "status": "started",
        "message": "Deployment started in background"
    }

@router.get("/deployment/{deployment_id}/status")
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

@router.get("/user/{user_id}/terraform")
async def get_user_terraform(user_id: str):
    """
    Get all terraform configurations for a user
    """
    user_terraform = get_user_terraform_plans(user_id)
    return {"terraform_configs": user_terraform}

@router.get("/user/{user_id}/deployments")
async def get_user_deployments_endpoint(user_id: str):
    """
    Get all deployments for a user
    """
    user_deployments = get_user_deployments(user_id)
    return {"deployments": user_deployments}

@router.post("/destroy")
async def destroy_terraform_endpoint(
    request: DestroyRequest,
    background_tasks: BackgroundTasks
):
    """
    Destroy terraform infrastructure in user's AWS account
    """
    # Get user's role ARN
    user = get_user(request.user_id)
    if not user or 'roleArn' not in user:
        raise HTTPException(status_code=400, detail="AWS account not connected")
    
    # Get terraform code
    tf_record = get_terraform_plan(request.terraform_id)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Get external ID
    external_id = user.get("externalId")
    if not external_id:
        raise HTTPException(status_code=400, detail="External ID not found")
    
    # Create deployment record for destroy operation
    doc_ref = db.collection("deployments").document()
    doc_ref.set({
        "operation": "destroy",
        "status": "destroying",
        "user_id": request.user_id,
        "terraform_id": request.terraform_id,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "output": ""
    })
    
    # Run destroy in background
    background_tasks.add_task(
        execute_terraform_destroy,
        request.deployment_id,
        user['roleArn'],
        external_id,
        tf_record['terraformCode']
    )
    
    return {
        "deployment_id": request.deployment_id,
        "status": "destroying",
        "message": "Destroy operation started in background"
    }

@router.get("/terraform/{terraform_id}/resources")
async def get_terraform_resources(terraform_id: str):
    """
    Get the current state of deployed resources
    This would require implementing terraform state management
    """
    tf_record = get_terraform_plan(terraform_id)
    if not tf_record:
        raise HTTPException(status_code=404, detail="Terraform code not found")
    
    # Find all deployments for this terraform
    doc_ref = db.collection("deployments").where("terraform_id", "==", terraform_id)
    docs = doc_ref.stream()
    
    # Get the latest successful deployment
    successful_deployments = [
        dep for dep in docs
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
