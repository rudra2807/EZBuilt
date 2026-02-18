from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import uuid

from .models import User, AWSIntegration, IntegrationStatus

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: str, email: str) -> User:
        """Create user with Cognito sub as user_id"""
        user = User(user_id=user_id, email=email)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(last_login=datetime.utcnow())
        )
        await self.session.commit()
    
    async def get_or_create(self, user_id: str, email: str) -> User:
        """Get or create user with Cognito sub"""
        user = await self.get_by_id(user_id)
        if not user:
            user = await self.create(user_id=user_id, email=email)
        return user

class AWSIntegrationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        external_id: str,
        aws_account_id: Optional[str] = None,
        role_arn: Optional[str] = None
    ) -> AWSIntegration:
        integration = AWSIntegration(
            user_id=user_id,
            external_id=external_id,
            aws_account_id=aws_account_id,
            role_arn=role_arn,
            status=IntegrationStatus.PENDING
        )
        self.session.add(integration)
        await self.session.commit()
        await self.session.refresh(integration)
        return integration
    
    async def get_by_external_id(self, external_id: str) -> Optional[AWSIntegration]:
        result = await self.session.execute(
            select(AWSIntegration)
            .options(selectinload(AWSIntegration.user))
            .where(AWSIntegration.external_id == external_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: str) -> List[AWSIntegration]:
        result = await self.session.execute(
            select(AWSIntegration)
            .where(AWSIntegration.user_id == user_id)
            .order_by(AWSIntegration.created_at.desc())
        )
        return result.scalars().all()
    
    async def update_status(
        self,
        integration_id: uuid.UUID,
        status: IntegrationStatus,
        role_arn: Optional[str] = None,
        aws_account_id: Optional[str] = None
    ) -> None:
        values = {"status": status}
        if status == IntegrationStatus.CONNECTED:
            values["verified_at"] = datetime.utcnow()
        if role_arn:
            values["role_arn"] = role_arn
        if aws_account_id:
            values["aws_account_id"] = aws_account_id
        
        await self.session.execute(
            update(AWSIntegration)
            .where(AWSIntegration.id == integration_id)
            .values(**values)
        )
        await self.session.commit()
    
    async def get_active_integration(self, user_id: str) -> Optional[AWSIntegration]:
        """Get the most recent connected integration for a user"""
        result = await self.session.execute(
            select(AWSIntegration)
            .where(
                AWSIntegration.user_id == user_id,
                AWSIntegration.status == IntegrationStatus.CONNECTED
            )
            .order_by(AWSIntegration.verified_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
