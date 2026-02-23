from sqlalchemy.ext.asyncio import AsyncSession
from src.database import UserRepository
from typing import Dict

async def handle_cognito_user(db: AsyncSession, cognito_user: Dict) -> Dict:
    """
    Handle Cognito user authentication and sync with database
    
    Args:
        db: Database session
        cognito_user: Cognito user data from token/API
            Expected format: {
                'sub': 'cognito-user-id',
                'email': 'user@example.com',
                ...
            }
    
    Returns:
        User data dictionary
    """
    user_repo = UserRepository(db)
    
    # Extract Cognito sub and email
    user_id = cognito_user.get('sub')
    email = cognito_user.get('email')
    
    if not user_id or not email:
        raise ValueError("Missing required Cognito attributes: sub and email")
    
    # Get or create user with Cognito sub as user_id
    user = await user_repo.get_or_create(user_id=user_id, email=email)
    
    # Update last login
    await user_repo.update_last_login(user_id)
    
    return {
        'user_id': user.user_id,
        'email': user.email,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    }
