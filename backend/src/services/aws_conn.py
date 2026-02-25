import uuid
from datetime import datetime
import boto3
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories import AWSIntegrationRepository

def generate_external_id(user_id: str) -> str:
    """Generate unique external ID for cross-account access"""
    return f"ezbuilt-{user_id}-{uuid.uuid4().hex[:8]}"

# def save_pending_connection(user_id: str, external_id: str):
#     """Save pending connection to database"""
#     connections_db[external_id] = {
#         'user_id': user_id,
#         'external_id': external_id,
#         'status': 'pending',
#         'created_at': datetime.utcnow().isoformat()
#     }

async def get_user_by_external_id(external_id: str, db: AsyncSession):
    """Get user by external ID from PostgreSQL"""
    repo = AWSIntegrationRepository(db)
    integration = await repo.get_by_external_id(external_id)
    
    if not integration:
        return None
    
    return {
        'user_id': integration.user_id,
        'external_id': integration.external_id,
        'roleArn': integration.role_arn
    }

# def save_role_arn(user_id: str, role_arn: str):
#     """Save role ARN to user record"""
#     if user_id not in users_db:
#         users_db[user_id] = {}
    
#     users_db[user_id]['role_arn'] = role_arn
#     users_db[user_id]['connected_at'] = datetime.utcnow().isoformat()
    
#     # Update connection status
#     for external_id, conn in connections_db.items():
#         if conn['user_id'] == user_id:
#             connections_db[external_id]['status'] = 'connected'
#             connections_db[external_id]['role_arn'] = role_arn

async def get_user(user_id: str, db: AsyncSession):
    """Get user's AWS connection from PostgreSQL"""
    repo = AWSIntegrationRepository(db)
    integration = await repo.get_active_integration(user_id)
    
    if not integration:
        return None
    
    return {
        'roleArn': integration.role_arn,
        'externalId': integration.external_id,
        'aws_account_id': integration.aws_account_id
    }

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