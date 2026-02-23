from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class IntegrationStatus(str, enum.Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"

class DeploymentStatus(str, enum.Enum):
    STARTED = "started"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DESTROYED = "destroyed"
    DESTROY_FAILED = "destroy_failed"

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(255), primary_key=True)  # Cognito sub attribute
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    aws_integrations = relationship("AWSIntegration", back_populates="user", cascade="all, delete-orphan")
    terraform_plans = relationship("TerraformPlan", back_populates="user", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="user", cascade="all, delete-orphan")

class AWSIntegration(Base):
    __tablename__ = "aws_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    aws_account_id = Column(String(12), nullable=True)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    role_arn = Column(String(255), nullable=True)
    status = Column(SQLEnum(IntegrationStatus), nullable=False, default=IntegrationStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="aws_integrations")

class TerraformPlan(Base):
    __tablename__ = "terraform_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    original_requirements = Column(Text, nullable=False)
    structured_requirements = Column(JSONB, nullable=False)
    s3_prefix = Column(String(500), nullable=False)
    validation_passed = Column(Boolean, default=False)
    validation_output = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='generating')
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="terraform_plans")
    deployments = relationship("Deployment", back_populates="terraform_plan", cascade="all, delete-orphan")

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    terraform_plan_id = Column(UUID(as_uuid=True), ForeignKey("terraform_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    aws_connection_id = Column(UUID(as_uuid=True), ForeignKey("aws_integrations.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(DeploymentStatus), nullable=False, default=DeploymentStatus.STARTED, index=True)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="deployments")
    terraform_plan = relationship("TerraformPlan", back_populates="deployments")
    aws_connection = relationship("AWSIntegration")
