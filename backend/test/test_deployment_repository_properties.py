"""
Property-based tests for DeploymentRepository user isolation.

Property: For any user and any resource type (deployment, terraform_plan, aws_integration),
when querying resources by user_id, the system should only return resources that belong
to that specific user and never expose resources belonging to other users.
"""

import pytest
import pytest_asyncio
import uuid
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

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
async def test_property_user_resource_isolation(db_session):
    """
    Property 1: User Resource Isolation
    
    For any two distinct users, when one user queries for deployments,
    they should only see their own deployments and never see deployments
    belonging to the other user.
    """
    # Create two distinct users
    user1_id = f"test-user-{uuid.uuid4()}"
    user2_id = f"test-user-{uuid.uuid4()}"
    email1 = f"user1-{uuid.uuid4()}@example.com"
    email2 = f"user2-{uuid.uuid4()}@example.com"
    
    user1 = User(user_id=user1_id, email=email1)
    user2 = User(user_id=user2_id, email=email2)
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    
    # Create AWS integrations for both users
    aws_conn1 = AWSIntegration(
        user_id=user1_id,
        external_id=f"ext-{uuid.uuid4()}",
        aws_account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/TestRole1",
        status=IntegrationStatus.CONNECTED
    )
    aws_conn2 = AWSIntegration(
        user_id=user2_id,
        external_id=f"ext-{uuid.uuid4()}",
        aws_account_id="123456789013",
        role_arn="arn:aws:iam::123456789013:role/TestRole2",
        status=IntegrationStatus.CONNECTED
    )
    db_session.add(aws_conn1)
    db_session.add(aws_conn2)
    await db_session.commit()
    await db_session.refresh(aws_conn1)
    await db_session.refresh(aws_conn2)
    
    # Create terraform plans for both users
    plan1 = TerraformPlan(
        user_id=user1_id,
        original_requirements="User 1 requirements",
        structured_requirements={"resources": ["ec2"]},
        s3_prefix=f"terraform/user1/{uuid.uuid4()}/",
        status="completed"
    )
    plan2 = TerraformPlan(
        user_id=user2_id,
        original_requirements="User 2 requirements",
        structured_requirements={"resources": ["s3"]},
        s3_prefix=f"terraform/user2/{uuid.uuid4()}/",
        status="completed"
    )
    db_session.add(plan1)
    db_session.add(plan2)
    await db_session.commit()
    await db_session.refresh(plan1)
    await db_session.refresh(plan2)
    
    # Create deployments for both users
    deployment_repo = DeploymentRepository(db_session)
    
    deployment1 = await deployment_repo.create(
        user_id=user1_id,
        terraform_plan_id=plan1.id,
        aws_connection_id=aws_conn1.id
    )
    
    deployment2 = await deployment_repo.create(
        user_id=user2_id,
        terraform_plan_id=plan2.id,
        aws_connection_id=aws_conn2.id
    )
    
    # Property Test 1: User 1 should only see their own deployment
    user1_deployment = await deployment_repo.get_by_id(deployment1.id, user1_id)
    assert user1_deployment is not None, "User 1 should be able to access their own deployment"
    assert user1_deployment.id == deployment1.id
    assert user1_deployment.user_id == user1_id
    
    # Property Test 2: User 1 should NOT see User 2's deployment
    user1_accessing_user2 = await deployment_repo.get_by_id(deployment2.id, user1_id)
    assert user1_accessing_user2 is None, "User 1 should NOT be able to access User 2's deployment"
    
    # Property Test 3: User 2 should only see their own deployment
    user2_deployment = await deployment_repo.get_by_id(deployment2.id, user2_id)
    assert user2_deployment is not None, "User 2 should be able to access their own deployment"
    assert user2_deployment.id == deployment2.id
    assert user2_deployment.user_id == user2_id
    
    # Property Test 4: User 2 should NOT see User 1's deployment
    user2_accessing_user1 = await deployment_repo.get_by_id(deployment1.id, user2_id)
    assert user2_accessing_user1 is None, "User 2 should NOT be able to access User 1's deployment"
    
    # Property Test 5: get_user_deployments should only return user's own deployments
    user1_deployments = await deployment_repo.get_user_deployments(user1_id)
    assert len(user1_deployments) >= 1, "User 1 should see at least 1 deployment"
    assert all(d.user_id == user1_id for d in user1_deployments), "All deployments should belong to User 1"
    assert deployment1.id in [d.id for d in user1_deployments], "User 1's deployment should be in the list"
    assert deployment2.id not in [d.id for d in user1_deployments], "User 2's deployment should NOT be in User 1's list"
    
    user2_deployments = await deployment_repo.get_user_deployments(user2_id)
    assert len(user2_deployments) >= 1, "User 2 should see at least 1 deployment"
    assert all(d.user_id == user2_id for d in user2_deployments), "All deployments should belong to User 2"
    assert deployment2.id in [d.id for d in user2_deployments], "User 2's deployment should be in the list"
    assert deployment1.id not in [d.id for d in user2_deployments], "User 1's deployment should NOT be in User 2's list"
    
    # Property Test 6: Verify terraform_plan isolation through repository
    plan_repo = TerraformPlanRepository(db_session)
    
    # User 1 should be able to access their own plan
    user1_plan = await plan_repo.get_plan(plan1.id)
    assert user1_plan is not None
    assert user1_plan.user_id == user1_id
    
    # User 2 should be able to access their own plan
    user2_plan = await plan_repo.get_plan(plan2.id)
    assert user2_plan is not None
    assert user2_plan.user_id == user2_id
    
    # Verify user-specific plan queries
    user1_plans = await plan_repo.get_user_plans(user1_id)
    assert all(p.user_id == user1_id for p in user1_plans), "All plans should belong to User 1"
    assert plan1.id in [p.id for p in user1_plans], "User 1's plan should be in their list"
    assert plan2.id not in [p.id for p in user1_plans], "User 2's plan should NOT be in User 1's list"
    
    user2_plans = await plan_repo.get_user_plans(user2_id)
    assert all(p.user_id == user2_id for p in user2_plans), "All plans should belong to User 2"
    assert plan2.id in [p.id for p in user2_plans], "User 2's plan should be in their list"
    assert plan1.id not in [p.id for p in user2_plans], "User 1's plan should NOT be in User 2's list"
    
    # Property Test 7: Verify aws_integration isolation through repository
    aws_repo = AWSIntegrationRepository(db_session)
    
    # User 1 should only see their own AWS connections
    user1_aws_conns = await aws_repo.get_by_user_id(user1_id)
    assert len(user1_aws_conns) >= 1
    assert all(conn.user_id == user1_id for conn in user1_aws_conns), "All connections should belong to User 1"
    assert aws_conn1.id in [c.id for c in user1_aws_conns], "User 1's connection should be in their list"
    assert aws_conn2.id not in [c.id for c in user1_aws_conns], "User 2's connection should NOT be in User 1's list"
    
    # User 2 should only see their own AWS connections
    user2_aws_conns = await aws_repo.get_by_user_id(user2_id)
    assert len(user2_aws_conns) >= 1
    assert all(conn.user_id == user2_id for conn in user2_aws_conns), "All connections should belong to User 2"
    assert aws_conn2.id in [c.id for c in user2_aws_conns], "User 2's connection should be in their list"
    assert aws_conn1.id not in [c.id for c in user2_aws_conns], "User 1's connection should NOT be in User 2's list"


@pytest.mark.asyncio
async def test_property_user_cascade_delete(db_session):
    """
    Property 2: User Cascade Delete
    
    For any user with associated deployments, when the user is deleted from the database,
    all deployments belonging to that user should also be deleted (CASCADE behavior).
    """
    # Create a user
    user_id = f"test-user-cascade-{uuid.uuid4()}"
    email = f"cascade-{uuid.uuid4()}@example.com"
    
    user = User(user_id=user_id, email=email)
    db_session.add(user)
    await db_session.commit()
    
    # Create AWS integration for the user
    aws_conn = AWSIntegration(
        user_id=user_id,
        external_id=f"ext-cascade-{uuid.uuid4()}",
        aws_account_id="123456789014",
        role_arn="arn:aws:iam::123456789014:role/CascadeTestRole",
        status=IntegrationStatus.CONNECTED
    )
    db_session.add(aws_conn)
    await db_session.commit()
    await db_session.refresh(aws_conn)
    
    # Create terraform plan for the user
    plan = TerraformPlan(
        user_id=user_id,
        original_requirements="Cascade test requirements",
        structured_requirements={"resources": ["ec2"]},
        s3_prefix=f"terraform/cascade/{uuid.uuid4()}/",
        status="completed"
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    
    # Create multiple deployments for the user
    deployment_repo = DeploymentRepository(db_session)
    
    deployment1 = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=plan.id,
        aws_connection_id=aws_conn.id
    )
    
    deployment2 = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=plan.id,
        aws_connection_id=aws_conn.id
    )
    
    deployment1_id = deployment1.id
    deployment2_id = deployment2.id
    
    # Verify deployments exist
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment1_id)
    )
    assert result.scalar_one_or_none() is not None, "Deployment 1 should exist before user deletion"
    
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment2_id)
    )
    assert result.scalar_one_or_none() is not None, "Deployment 2 should exist before user deletion"
    
    # Delete the user
    await db_session.delete(user)
    await db_session.commit()
    
    # Property: All deployments belonging to the deleted user should be CASCADE deleted
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment1_id)
    )
    assert result.scalar_one_or_none() is None, "Deployment 1 should be CASCADE deleted when user is deleted"
    
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment2_id)
    )
    assert result.scalar_one_or_none() is None, "Deployment 2 should be CASCADE deleted when user is deleted"


@pytest.mark.asyncio
async def test_property_plan_cascade_delete(db_session):
    """
    Property 3: Plan Cascade Delete
    
    For any terraform_plan with associated deployments, when the plan is deleted from the database,
    all deployments referencing that plan should also be deleted (CASCADE behavior).
    """
    # Create a user
    user_id = f"test-user-plan-cascade-{uuid.uuid4()}"
    email = f"plan-cascade-{uuid.uuid4()}@example.com"
    
    user = User(user_id=user_id, email=email)
    db_session.add(user)
    await db_session.commit()
    
    # Create AWS integration for the user
    aws_conn = AWSIntegration(
        user_id=user_id,
        external_id=f"ext-plan-cascade-{uuid.uuid4()}",
        aws_account_id="123456789015",
        role_arn="arn:aws:iam::123456789015:role/PlanCascadeTestRole",
        status=IntegrationStatus.CONNECTED
    )
    db_session.add(aws_conn)
    await db_session.commit()
    await db_session.refresh(aws_conn)
    
    # Create terraform plan for the user
    plan = TerraformPlan(
        user_id=user_id,
        original_requirements="Plan cascade test requirements",
        structured_requirements={"resources": ["s3"]},
        s3_prefix=f"terraform/plan-cascade/{uuid.uuid4()}/",
        status="completed"
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    plan_id = plan.id
    
    # Create multiple deployments referencing the plan
    deployment_repo = DeploymentRepository(db_session)
    
    deployment1 = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=plan.id,
        aws_connection_id=aws_conn.id
    )
    
    deployment2 = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=plan.id,
        aws_connection_id=aws_conn.id
    )
    
    deployment1_id = deployment1.id
    deployment2_id = deployment2.id
    
    # Verify deployments exist
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment1_id)
    )
    assert result.scalar_one_or_none() is not None, "Deployment 1 should exist before plan deletion"
    
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment2_id)
    )
    assert result.scalar_one_or_none() is not None, "Deployment 2 should exist before plan deletion"
    
    # Delete the terraform plan
    await db_session.delete(plan)
    await db_session.commit()
    
    # Property: All deployments referencing the deleted plan should be CASCADE deleted
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment1_id)
    )
    assert result.scalar_one_or_none() is None, "Deployment 1 should be CASCADE deleted when plan is deleted"
    
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment2_id)
    )
    assert result.scalar_one_or_none() is None, "Deployment 2 should be CASCADE deleted when plan is deleted"


@pytest.mark.asyncio
async def test_property_connection_set_null(db_session):
    """
    Property 4: Connection Set Null
    
    For any deployment with an associated aws_integration, when the aws_integration is deleted
    from the database, the deployment's aws_connection_id should be set to NULL (SET NULL behavior)
    and the deployment record should remain.
    """
    # Create a user
    user_id = f"test-user-conn-null-{uuid.uuid4()}"
    email = f"conn-null-{uuid.uuid4()}@example.com"
    
    user = User(user_id=user_id, email=email)
    db_session.add(user)
    await db_session.commit()
    
    # Create AWS integration for the user
    aws_conn = AWSIntegration(
        user_id=user_id,
        external_id=f"ext-conn-null-{uuid.uuid4()}",
        aws_account_id="123456789016",
        role_arn="arn:aws:iam::123456789016:role/ConnNullTestRole",
        status=IntegrationStatus.CONNECTED
    )
    db_session.add(aws_conn)
    await db_session.commit()
    await db_session.refresh(aws_conn)
    aws_conn_id = aws_conn.id
    
    # Create terraform plan for the user
    plan = TerraformPlan(
        user_id=user_id,
        original_requirements="Connection null test requirements",
        structured_requirements={"resources": ["rds"]},
        s3_prefix=f"terraform/conn-null/{uuid.uuid4()}/",
        status="completed"
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    
    # Create deployment referencing the AWS connection
    deployment_repo = DeploymentRepository(db_session)
    
    deployment = await deployment_repo.create(
        user_id=user_id,
        terraform_plan_id=plan.id,
        aws_connection_id=aws_conn.id
    )
    
    deployment_id = deployment.id
    plan_id = plan.id
    
    # Verify deployment exists with aws_connection_id set
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment_id)
    )
    deployment_before = result.scalar_one_or_none()
    assert deployment_before is not None, "Deployment should exist before connection deletion"
    assert deployment_before.aws_connection_id == aws_conn_id, "Deployment should reference the AWS connection"
    
    # Delete the AWS integration
    await db_session.delete(aws_conn)
    await db_session.commit()
    
    # Expire all objects to force fresh query from database
    db_session.expire_all()
    
    # Property: Deployment should still exist but aws_connection_id should be NULL
    result = await db_session.execute(
        select(Deployment).where(Deployment.id == deployment_id)
    )
    deployment_after = result.scalar_one_or_none()
    
    assert deployment_after is not None, "Deployment should still exist after connection deletion (not CASCADE deleted)"
    assert deployment_after.aws_connection_id is None, "Deployment aws_connection_id should be SET NULL when connection is deleted"
    assert deployment_after.user_id == user_id, "Deployment should still belong to the same user"
    assert deployment_after.terraform_plan_id == plan_id, "Deployment should still reference the same plan"
