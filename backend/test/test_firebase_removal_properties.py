"""
Property-based tests for Firebase Removal and Consolidation.

This test validates that the refactoring to remove Firebase/Firestore and consolidate
to PostgreSQL maintains data persistence correctness.

Feature: firebase-removal-and-consolidation
"""

import pytest
import pytest_asyncio
import uuid
import os
import sys
from hypothesis import given, strategies as st, settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import User, TerraformPlan, AWSIntegration, Deployment, DeploymentStatus, IntegrationStatus
from src.database.repositories import DeploymentRepository, TerraformPlanRepository, AWSIntegrationRepository


# Use local test database
DATABASE_URL = "postgresql+asyncpg://postgres:master@localhost:5432/ezbuilt_test"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine (fresh for each test)"""
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Create a test database session"""
    AsyncSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.mark.asyncio
@given(
    random_suffix=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=10,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
async def test_property_deployment_persistence_postgresql(random_suffix):
    """
    Property 1: Deployment persistence in PostgreSQL
    
    For any valid deployment creation request with user_id, terraform_plan_id, 
    and aws_connection_id, after the deployment is created, querying the PostgreSQL 
    deployments table should return a record with matching IDs and status STARTED.
    
    **Validates: Requirements 17.1**
    
    Feature: firebase-removal-and-consolidation, Property 1: Deployment persistence in PostgreSQL
    """
    # Generate unique IDs for this test run to avoid conflicts
    user_id = f"test-user-{uuid.uuid4()}-{random_suffix}"
    terraform_plan_id = uuid.uuid4()
    aws_connection_id = uuid.uuid4()
    
    # Create fresh database session for this test
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup: Create user
            email = f"{user_id}@example.com"
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Setup: Create AWS integration
            aws_conn = AWSIntegration(
                id=aws_connection_id,
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            
            # Setup: Create terraform plan
            plan = TerraformPlan(
                id=terraform_plan_id,
                user_id=user_id,
                original_requirements="Test requirements",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=f"terraform/{user_id}/{terraform_plan_id}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            
            # Action: Create deployment using repository
            repo = DeploymentRepository(db_session)
            deployment = await repo.create(
                user_id=user_id,
                terraform_plan_id=terraform_plan_id,
                aws_connection_id=aws_connection_id
            )
            
            # Property Verification: Query from database and verify persistence
            retrieved = await repo.get_by_id(deployment.id, user_id)
            
            # Assert: Deployment persists to PostgreSQL with correct data
            assert retrieved is not None, "Deployment should persist to PostgreSQL"
            assert retrieved.user_id == user_id, f"Expected user_id {user_id}, got {retrieved.user_id}"
            assert retrieved.terraform_plan_id == terraform_plan_id, f"Expected terraform_plan_id {terraform_plan_id}, got {retrieved.terraform_plan_id}"
            assert retrieved.aws_connection_id == aws_connection_id, f"Expected aws_connection_id {aws_connection_id}, got {retrieved.aws_connection_id}"
            assert retrieved.status == DeploymentStatus.STARTED, f"Expected status STARTED, got {retrieved.status}"
            assert retrieved.id == deployment.id, "Retrieved deployment ID should match created deployment ID"
            
        finally:
            # Cleanup
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@given(
    random_suffix=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=10,
        max_size=20
    ),
    requirements_text=st.text(
        alphabet=st.characters(
            min_codepoint=32,  # Space character
            max_codepoint=126,  # Tilde character (printable ASCII)
            blacklist_categories=('Cc', 'Cs')  # Exclude control and surrogate characters
        ),
        min_size=1,
        max_size=500
    ),
    resource_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
async def test_property_terraform_plan_persistence_postgresql(random_suffix, requirements_text, resource_count):
    """
    Property 2: Terraform plan persistence in PostgreSQL
    
    For any valid Terraform plan creation with user_id, requirements, and structured_requirements,
    after the plan is created, querying the PostgreSQL terraform_plans table should return a 
    record with matching user_id and requirements.
    
    **Validates: Requirements 17.2**
    
    Feature: firebase-removal-and-consolidation, Property 2: Terraform plan persistence in PostgreSQL
    """
    # Generate unique IDs for this test run to avoid conflicts
    user_id = f"test-user-{uuid.uuid4()}-{random_suffix}"
    
    # Generate structured requirements based on resource count
    structured_requirements = {
        "resources": [f"resource-{i}" for i in range(resource_count)],
        "region": "us-east-1",
        "count": resource_count
    }
    
    # Create fresh database session for this test
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup: Create user
            email = f"{user_id}@example.com"
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Action: Create terraform plan using repository
            repo = TerraformPlanRepository(db_session)
            s3_prefix = f"terraform/{user_id}/{uuid.uuid4()}/"
            
            plan = await repo.create_plan(
                user_id=user_id,
                original_requirements=requirements_text,
                structured_requirements=structured_requirements,
                s3_prefix=s3_prefix
            )
            
            # Property Verification: Query from database and verify persistence
            retrieved = await repo.get_plan(plan.id)
            
            # Assert: Terraform plan persists to PostgreSQL with correct data
            assert retrieved is not None, "Terraform plan should persist to PostgreSQL"
            assert retrieved.user_id == user_id, f"Expected user_id {user_id}, got {retrieved.user_id}"
            assert retrieved.original_requirements == requirements_text, f"Expected requirements '{requirements_text}', got '{retrieved.original_requirements}'"
            assert retrieved.structured_requirements == structured_requirements, f"Expected structured_requirements {structured_requirements}, got {retrieved.structured_requirements}"
            assert retrieved.s3_prefix == s3_prefix, f"Expected s3_prefix {s3_prefix}, got {retrieved.s3_prefix}"
            assert retrieved.status == 'generating', f"Expected status 'generating', got {retrieved.status}"
            assert retrieved.id == plan.id, "Retrieved plan ID should match created plan ID"
            
            # Additional verification: Ensure plan appears in user's plan list
            user_plans = await repo.get_user_plans(user_id)
            assert len(user_plans) > 0, "User should have at least one plan"
            assert any(p.id == plan.id for p in user_plans), "Created plan should appear in user's plan list"
            
        finally:
            # Cleanup
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@given(
    random_suffix=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=10,
        max_size=20
    ),
    external_id_suffix=st.text(
        alphabet=st.characters(
            min_codepoint=48,  # '0'
            max_codepoint=122,  # 'z'
            blacklist_categories=('Cc', 'Cs')  # Exclude control and surrogate characters
        ),
        min_size=10,
        max_size=30
    ),
    aws_account_id=st.integers(min_value=100000000000, max_value=999999999999)
)
@settings(max_examples=100, deadline=None)
async def test_property_aws_connection_persistence_postgresql(random_suffix, external_id_suffix, aws_account_id):
    """
    Property 3: AWS connection persistence in PostgreSQL
    
    For any valid AWS connection creation with user_id and external_id, after the 
    connection is created, querying the PostgreSQL aws_integrations table should 
    return a record with matching user_id and external_id.
    
    **Validates: Requirements 17.3**
    
    Feature: firebase-removal-and-consolidation, Property 3: AWS connection persistence in PostgreSQL
    """
    # Generate unique IDs for this test run to avoid conflicts
    user_id = f"test-user-{uuid.uuid4()}-{random_suffix}"
    external_id = f"ext-{uuid.uuid4()}-{external_id_suffix}"
    aws_account_id_str = str(aws_account_id)
    role_arn = f"arn:aws:iam::{aws_account_id_str}:role/TestRole"
    
    # Create fresh database session for this test
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Setup: Create user
            email = f"{user_id}@example.com"
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Action: Create AWS connection using repository
            repo = AWSIntegrationRepository(db_session)
            connection = await repo.create(
                user_id=user_id,
                external_id=external_id,
                aws_account_id=aws_account_id_str,
                role_arn=role_arn
            )
            
            # Property Verification: Query from database and verify persistence
            retrieved = await repo.get_by_external_id(external_id)
            
            # Assert: AWS connection persists to PostgreSQL with correct data
            assert retrieved is not None, "AWS connection should persist to PostgreSQL"
            assert retrieved.user_id == user_id, f"Expected user_id {user_id}, got {retrieved.user_id}"
            assert retrieved.external_id == external_id, f"Expected external_id {external_id}, got {retrieved.external_id}"
            assert retrieved.aws_account_id == aws_account_id_str, f"Expected aws_account_id {aws_account_id_str}, got {retrieved.aws_account_id}"
            assert retrieved.role_arn == role_arn, f"Expected role_arn {role_arn}, got {retrieved.role_arn}"
            assert retrieved.id == connection.id, "Retrieved connection ID should match created connection ID"
            
            # Additional verification: Ensure connection can be retrieved by user_id
            user_connections = await repo.get_by_user_id(user_id)
            assert len(user_connections) > 0, "User should have at least one connection"
            assert any(c.id == connection.id for c in user_connections), "Created connection should appear in user's connection list"
            assert any(c.external_id == external_id for c in user_connections), "Created connection should have matching external_id"
            
        finally:
            # Cleanup
            await db_session.rollback()
            await engine.dispose()
