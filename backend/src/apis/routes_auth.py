from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from src.database import get_db
from src.services.auth_service import handle_cognito_user

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class CognitoUserData(BaseModel):
    sub: str
    email: EmailStr
    name: str | None = None

class UserResponse(BaseModel):
    user_id: str
    email: str
    created_at: str
    last_login: str | None

@router.post("/sync-user", response_model=UserResponse)
async def sync_user(user_data: CognitoUserData, db: AsyncSession = Depends(get_db)):
    """
    Sync Cognito user to database after successful login
    Called from frontend after OAuth callback
    """
    try:
        user = await handle_cognito_user(
            db=db,
            cognito_user={
                'sub': user_data.sub,
                'email': user_data.email,
                'name': user_data.name
            }
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync user: {str(e)}")

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get user information by user_id (Cognito sub)
    """
    from src.database import UserRepository
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        'user_id': user.user_id,
        'email': user.email,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    }
