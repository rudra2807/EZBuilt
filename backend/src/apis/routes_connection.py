from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.aws_conn import assume_role, generate_external_id
from src.utilities.schemas import CFNLinkRequest, RoleArnCallback
from src.database import get_db, UserRepository, AWSIntegrationRepository, IntegrationStatus
from datetime import datetime


router = APIRouter(prefix="/api", tags=["connections"])

@router.post("/generate-cfn-link")
async def generate_cfn_link(request: CFNLinkRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate CloudFormation quick-create link for account connection
    """
    user_repo = UserRepository(db)
    integration_repo = AWSIntegrationRepository(db)
    
    # Get or create user
    user = await user_repo.get_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    external_id = generate_external_id(str(request.user_id))
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
    
    # Save pending connection to database
    await integration_repo.create(
        user_id=request.user_id,
        external_id=external_id
    )
    
    return {
        "cfn_link": cfn_link,
        "external_id": external_id,
        "instructions": "Click the link, review permissions, and create the CloudFormation stack"
    }

@router.post("/cfn-callback")
async def cfn_callback(data: RoleArnCallback, db: AsyncSession = Depends(get_db)):
    """
    Receives ARN from CloudFormation after stack creation
    """
    integration_repo = AWSIntegrationRepository(db)
    
    integration = await integration_repo.get_by_external_id(data.external_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Invalid external_id")
    
    # Test role assumption
    try:
        assume_role(data.role_arn, data.external_id)
        
        # Update integration status
        await integration_repo.update_status(
            integration_id=integration.id,
            status=IntegrationStatus.CONNECTED,
            role_arn=data.role_arn
        )
        
        return {"status": "success", "message": "Role connected successfully"}
    except Exception as e:
        await integration_repo.update_status(
            integration_id=integration.id,
            status=IntegrationStatus.FAILED
        )
        return {"status": "error", "message": f"Role assumption failed: {str(e)}"}

@router.get("/connection-status/{external_id}")
async def get_connection_status(external_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get connection status for polling
    """
    integration_repo = AWSIntegrationRepository(db)
    
    integration = await integration_repo.get_by_external_id(external_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return {
        "connected": integration.status == IntegrationStatus.CONNECTED,
        "status": integration.status.value,
        "role_arn": integration.role_arn
    }

@router.post("/connect-account-manual")
async def connect_account_manual(
    user_id: str,
    role_arn: str,
    external_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manual connection method (for MVP without callback)
    User provides role ARN directly
    """
    integration_repo = AWSIntegrationRepository(db)
    
    integration = await integration_repo.get_by_external_id(external_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    try:
        # Test assume role
        assume_role(role_arn, external_id)
        
        # Update connection
        await integration_repo.update_status(
            integration_id=integration.id,
            status=IntegrationStatus.CONNECTED,
            role_arn=role_arn
        )
        
        return {
            "status": "success",
            "message": "AWS account connected successfully",
            "role_arn": role_arn
        }
    except Exception as e:
        await integration_repo.update_status(
            integration_id=integration.id,
            status=IntegrationStatus.FAILED
        )
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

@router.get("/user/{user_id}/aws-connections")
async def get_user_aws_connections(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all AWS connections for a user
    """
    integration_repo = AWSIntegrationRepository(db)

    connections = await integration_repo.get_by_user_id(user_id)

    # Convert to dict format for response
    connection_list = []
    for conn in connections:
        connection_list.append({
            "id": str(conn.id),
            "user_id": conn.user_id,
            "aws_account_id": conn.aws_account_id,
            "external_id": conn.external_id,
            "role_arn": conn.role_arn,
            "status": conn.status.value,
            "created_at": conn.created_at.isoformat() if conn.created_at else None,
            "verified_at": conn.verified_at.isoformat() if conn.verified_at else None
        })

    return {"connections": connection_list}
