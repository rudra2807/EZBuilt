from fastapi import APIRouter, HTTPException
from src.services.aws_conn import assume_role, generate_external_id, get_user_by_external_id
from src.utilities.schemas import CFNLinkRequest, RoleArnCallback


router = APIRouter(prefix="/api", tags=["connections"])

@router.post("/generate-cfn-link")
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
    # save_pending_connection(request.user_id, external_id)
    
    return {
        "cfn_link": cfn_link,
        "external_id": external_id,
        "instructions": "Click the link, review permissions, and create the CloudFormation stack"
    }

@router.post("/cfn-callback")
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
        # save_role_arn(user['user_id'], data.role_arn)
        return {"status": "success", "message": "Role connected successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Role assumption failed: {str(e)}"}

@router.get("/connection-status/{external_id}")
async def get_connection_status(external_id: str):
    """
    Get connection status for polling
    """
    user = get_user_by_external_id(external_id)
    if not user:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return {
        "connected": 'roleArn' in user,
        "status": 'connected' if 'roleArn' in user else 'pending',
        "role_arn": user.get('roleArn')
    }

@router.post("/connect-account-manual")
async def connect_account_manual(user_id: str, role_arn: str, external_id: str):
    """
    Manual connection method (for MVP without callback)
    User provides role ARN directly
    """
    try:
        # Test assume role
        assume_role(role_arn, external_id)
        
        # Save connection
        # save_role_arn(user_id, role_arn)
        
        return {
            "status": "success",
            "message": "AWS account connected successfully",
            "role_arn": role_arn
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
