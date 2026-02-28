"""
Property-based tests for deployment history API.

This test validates Property 1: User Plan Retrieval Completeness

Property: For any user with a set of TerraformPlans, when querying the History API
with that user's ID, the response should include all and only the plans belonging
to that user.
"""

import pytest
import pytest_asyncio
import uuid
import os
import sys
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import User, TerraformPlan, Deployment, DeploymentStatus
from src.database.repositories import TerraformPlanRepository


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


# Hypothesis strategies for generating test data
@st.composite
def user_id_strategy(draw):
    """Generate random user IDs"""
    return f"test-user-{draw(st.uuids())}"


@st.composite
def terraform_plan_strategy(draw, user_id: str):
    """Generate random TerraformPlan data"""
    return {
        "user_id": user_id,
        "original_requirements": draw(st.text(min_size=10, max_size=500)),
        "structured_requirements": {"resources": draw(st.lists(st.sampled_from(["ec2", "s3", "rds", "lambda"]), min_size=1, max_size=5))},
        "s3_prefix": f"terraform/{user_id}/{draw(st.uuids())}/",
        "status": draw(st.sampled_from(["generating", "completed", "failed"]))
    }


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_user1_plans=st.integers(min_value=0, max_value=10),
    num_user2_plans=st.integers(min_value=0, max_value=10),
    seed=st.integers(min_value=0, max_value=1000000)
)
async def test_property_user_plan_retrieval_completeness(
    num_user1_plans: int,
    num_user2_plans: int,
    seed: int
):
    """
    # Feature: deployment-history, Property 1: User Plan Retrieval Completeness
    
    Property: For any user with a set of TerraformPlans, when querying the
    get_user_plans_with_deployments method with that user's ID, the response
    should include all and only the plans belonging to that user.
    
    This test verifies:
    1. All plans belonging to user1 are returned when querying for user1
    2. No plans belonging to user2 are returned when querying for user1
    3. All plans belonging to user2 are returned when querying for user2
    4. No plans belonging to user1 are returned when querying for user2
    """
    # Create database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create two distinct users
            user1_id = f"test-user-prop1-{uuid.uuid4()}"
            user2_id = f"test-user-prop2-{uuid.uuid4()}"
            email1 = f"user1-prop1-{uuid.uuid4()}@example.com"
            email2 = f"user2-prop1-{uuid.uuid4()}@example.com"
            
            user1 = User(user_id=user1_id, email=email1)
            user2 = User(user_id=user2_id, email=email2)
            db_session.add(user1)
            db_session.add(user2)
            await db_session.commit()
            
            # Create random number of plans for user1
            user1_plan_ids = []
            for i in range(num_user1_plans):
                plan = TerraformPlan(
                    user_id=user1_id,
                    original_requirements=f"User 1 requirements {i} - seed {seed}",
                    structured_requirements={"resources": ["ec2", "s3"]},
                    s3_prefix=f"terraform/user1/{uuid.uuid4()}/",
                    status="completed"
                )
                db_session.add(plan)
                await db_session.flush()
                user1_plan_ids.append(plan.id)
            
            # Create random number of plans for user2
            user2_plan_ids = []
            for i in range(num_user2_plans):
                plan = TerraformPlan(
                    user_id=user2_id,
                    original_requirements=f"User 2 requirements {i} - seed {seed}",
                    structured_requirements={"resources": ["lambda", "rds"]},
                    s3_prefix=f"terraform/user2/{uuid.uuid4()}/",
                    status="completed"
                )
                db_session.add(plan)
                await db_session.flush()
                user2_plan_ids.append(plan.id)
            
            await db_session.commit()
            
            # Create repository instance
            plan_repo = TerraformPlanRepository(db_session)
            
            # Property Test 1: User 1 should get all and only their plans
            user1_plans = await plan_repo.get_user_plans_with_deployments(user1_id)
            user1_returned_ids = [p.id for p in user1_plans]
            
            # Verify all user1 plans are returned
            assert len(user1_returned_ids) == num_user1_plans, \
                f"User 1 should receive exactly {num_user1_plans} plans, got {len(user1_returned_ids)}"
            
            for plan_id in user1_plan_ids:
                assert plan_id in user1_returned_ids, \
                    f"User 1's plan {plan_id} should be in the returned results"
            
            # Verify no user2 plans are returned
            for plan_id in user2_plan_ids:
                assert plan_id not in user1_returned_ids, \
                    f"User 2's plan {plan_id} should NOT be in User 1's results"
            
            # Verify all returned plans belong to user1
            for plan in user1_plans:
                assert plan.user_id == user1_id, \
                    f"All returned plans should belong to User 1, but found plan with user_id {plan.user_id}"
            
            # Property Test 2: User 2 should get all and only their plans
            user2_plans = await plan_repo.get_user_plans_with_deployments(user2_id)
            user2_returned_ids = [p.id for p in user2_plans]
            
            # Verify all user2 plans are returned
            assert len(user2_returned_ids) == num_user2_plans, \
                f"User 2 should receive exactly {num_user2_plans} plans, got {len(user2_returned_ids)}"
            
            for plan_id in user2_plan_ids:
                assert plan_id in user2_returned_ids, \
                    f"User 2's plan {plan_id} should be in the returned results"
            
            # Verify no user1 plans are returned
            for plan_id in user1_plan_ids:
                assert plan_id not in user2_returned_ids, \
                    f"User 1's plan {plan_id} should NOT be in User 2's results"
            
            # Verify all returned plans belong to user2
            for plan in user2_plans:
                assert plan.user_id == user2_id, \
                    f"All returned plans should belong to User 2, but found plan with user_id {plan.user_id}"
        finally:
            # Clean up
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_plans=st.integers(min_value=1, max_value=5),
    deployments_per_plan=st.lists(st.integers(min_value=0, max_value=20), min_size=1, max_size=5),
    seed=st.integers(min_value=0, max_value=1000000)
)
async def test_property_deployment_count_accuracy(
    num_plans: int,
    deployments_per_plan: list[int],
    seed: int
):
    """
    # Feature: deployment-history, Property 4: Deployment Count Accuracy
    
    Property: For any TerraformPlan with associated Deployments, the deployment_count
    field in the API response should equal the actual number of Deployment records
    linked to that plan.
    
    This test verifies:
    1. Plans with 0 deployments have deployment_count = 0
    2. Plans with N deployments have deployment_count = N
    3. The count is accurate across multiple plans with varying deployment counts
    """
    # Create database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a test user
            user_id = f"test-user-prop4-{uuid.uuid4()}"
            email = f"user-prop4-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Ensure we have the right number of deployment counts
            deployment_counts = deployments_per_plan[:num_plans]
            if len(deployment_counts) < num_plans:
                deployment_counts.extend([0] * (num_plans - len(deployment_counts)))
            
            # Create plans with varying numbers of deployments
            plan_deployment_map = {}  # plan_id -> expected_count
            
            for i, num_deployments in enumerate(deployment_counts):
                # Create a TerraformPlan
                plan = TerraformPlan(
                    user_id=user_id,
                    original_requirements=f"Requirements for plan {i} - seed {seed}",
                    structured_requirements={"resources": ["ec2", "s3"]},
                    s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                    status="completed"
                )
                db_session.add(plan)
                await db_session.flush()
                
                # Create the specified number of deployments for this plan
                for j in range(num_deployments):
                    deployment = Deployment(
                        user_id=user_id,
                        terraform_plan_id=plan.id,
                        status=DeploymentStatus.SUCCESS,
                        created_at=datetime.now(timezone.utc)
                    )
                    db_session.add(deployment)
                
                plan_deployment_map[plan.id] = num_deployments
            
            await db_session.commit()
            
            # Create repository instance and fetch plans with deployments
            plan_repo = TerraformPlanRepository(db_session)
            plans = await plan_repo.get_user_plans_with_deployments(user_id)
            
            # Verify deployment count accuracy for each plan
            assert len(plans) == num_plans, \
                f"Should have created {num_plans} plans, but got {len(plans)}"
            
            for plan in plans:
                expected_count = plan_deployment_map[plan.id]
                actual_count = len(plan.deployments)
                
                assert actual_count == expected_count, \
                    f"Plan {plan.id} should have {expected_count} deployments, but has {actual_count}"
                
                # Also verify that the deployment_count field would be accurate
                # (This simulates what the API endpoint would calculate)
                deployment_count_field = len(plan.deployments)
                assert deployment_count_field == expected_count, \
                    f"Plan {plan.id} deployment_count field should be {expected_count}, but is {deployment_count_field}"
        finally:
            # Clean up
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_deployments=st.integers(min_value=2, max_value=10),
    seed=st.integers(min_value=0, max_value=1000000)
)
async def test_property_latest_deployment_status_display(
    num_deployments: int,
    seed: int
):
    """
    # Feature: deployment-history, Property 5: Latest Deployment Status Display
    
    Property: For any TerraformPlan with multiple Deployments, the displayed status
    should match the status of the Deployment with the most recent created_at timestamp.
    
    This test verifies:
    1. When multiple deployments exist with different timestamps, the latest one is identified
    2. The latest_deployment_status matches the status of the most recent deployment
    3. This holds true regardless of the order deployments are created in the database
    """
    # Create database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a test user
            user_id = f"test-user-prop5-{uuid.uuid4()}"
            email = f"user-prop5-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create a TerraformPlan
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Requirements for latest status test - seed {seed}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.flush()
            
            # Generate random timestamps and statuses for deployments
            # Use a base timestamp and add random offsets to ensure different times
            base_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            
            deployment_data = []
            all_statuses = [
                DeploymentStatus.SUCCESS,
                DeploymentStatus.FAILED,
                DeploymentStatus.RUNNING,
                DeploymentStatus.STARTED,
                DeploymentStatus.DESTROYED,
                DeploymentStatus.DESTROY_FAILED
            ]
            
            # Create deployments with incrementing timestamps
            for i in range(num_deployments):
                # Add i hours to base timestamp to ensure ordering
                timestamp = base_timestamp.replace(hour=(base_timestamp.hour + i) % 24, day=base_timestamp.day + (i // 24))
                status = all_statuses[i % len(all_statuses)]
                
                deployment_data.append({
                    "timestamp": timestamp,
                    "status": status
                })
            
            # Shuffle the order we insert them to test that ordering works correctly
            import random
            random.seed(seed)
            shuffled_data = deployment_data.copy()
            random.shuffle(shuffled_data)
            
            # Create deployments in shuffled order
            for data in shuffled_data:
                deployment = Deployment(
                    user_id=user_id,
                    terraform_plan_id=plan.id,
                    status=data["status"],
                    created_at=data["timestamp"]
                )
                db_session.add(deployment)
            
            await db_session.commit()
            
            # Determine the expected latest deployment status
            # Sort by timestamp descending to find the most recent
            sorted_data = sorted(deployment_data, key=lambda x: x["timestamp"], reverse=True)
            expected_latest_status = sorted_data[0]["status"]
            
            # Create repository instance and fetch plans with deployments
            plan_repo = TerraformPlanRepository(db_session)
            plans = await plan_repo.get_user_plans_with_deployments(user_id)
            
            # Verify we got the plan
            assert len(plans) == 1, f"Should have exactly 1 plan, got {len(plans)}"
            
            plan = plans[0]
            
            # Verify deployments are loaded
            assert len(plan.deployments) == num_deployments, \
                f"Plan should have {num_deployments} deployments, got {len(plan.deployments)}"
            
            # Verify deployments are ordered by created_at descending
            for i in range(len(plan.deployments) - 1):
                assert plan.deployments[i].created_at >= plan.deployments[i + 1].created_at, \
                    f"Deployments should be ordered by created_at descending"
            
            # The latest deployment should be the first one in the ordered list
            actual_latest_status = plan.deployments[0].status
            
            # Verify the latest deployment status matches expected
            assert actual_latest_status == expected_latest_status, \
                f"Latest deployment status should be {expected_latest_status}, but got {actual_latest_status}"
            
            # Also verify this is truly the deployment with the maximum created_at
            max_timestamp = max(d["timestamp"] for d in deployment_data)
            assert plan.deployments[0].created_at == max_timestamp, \
                f"First deployment should have the maximum timestamp {max_timestamp}, but has {plan.deployments[0].created_at}"
        finally:
            # Clean up
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_deployments=st.integers(min_value=2, max_value=15),
    seed=st.integers(min_value=0, max_value=1000000)
)
async def test_property_deployment_ordering(
    num_deployments: int,
    seed: int
):
    """
    # Feature: deployment-history, Property 7: Deployment Ordering
    
    Property: For any TerraformPlan with multiple Deployments, when returned by the
    get_user_plans_with_deployments method, the deployments should be ordered by
    created_at timestamp in descending order (newest first).
    
    This test verifies:
    1. Deployments are ordered by created_at descending
    2. For each adjacent pair, deployments[i].created_at >= deployments[i+1].created_at
    3. The ordering is maintained regardless of insertion order
    """
    # Create database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a test user
            user_id = f"test-user-prop7-{uuid.uuid4()}"
            email = f"user-prop7-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create a TerraformPlan
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Requirements for ordering test - seed {seed}",
                structured_requirements={"resources": ["ec2", "s3", "rds"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.flush()
            
            # Generate deployments with random timestamps
            # Use a base timestamp and add random offsets
            base_timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            
            import random
            random.seed(seed)
            
            deployment_timestamps = []
            all_statuses = [
                DeploymentStatus.SUCCESS,
                DeploymentStatus.FAILED,
                DeploymentStatus.RUNNING,
                DeploymentStatus.STARTED,
                DeploymentStatus.DESTROYED,
                DeploymentStatus.DESTROY_FAILED
            ]
            
            # Create deployments with random timestamps (spread over several days)
            for i in range(num_deployments):
                # Random offset in minutes (0 to 10080 minutes = 1 week)
                offset_minutes = random.randint(0, 10080)
                timestamp = base_timestamp.replace(
                    minute=(base_timestamp.minute + offset_minutes) % 60,
                    hour=(base_timestamp.hour + (offset_minutes // 60)) % 24,
                    day=base_timestamp.day + (offset_minutes // 1440)
                )
                deployment_timestamps.append(timestamp)
            
            # Shuffle the timestamps to insert in random order
            shuffled_timestamps = deployment_timestamps.copy()
            random.shuffle(shuffled_timestamps)
            
            # Create deployments in shuffled order
            for i, timestamp in enumerate(shuffled_timestamps):
                deployment = Deployment(
                    user_id=user_id,
                    terraform_plan_id=plan.id,
                    status=all_statuses[i % len(all_statuses)],
                    created_at=timestamp
                )
                db_session.add(deployment)
            
            await db_session.commit()
            
            # Create repository instance and fetch plans with deployments
            plan_repo = TerraformPlanRepository(db_session)
            plans = await plan_repo.get_user_plans_with_deployments(user_id)
            
            # Verify we got the plan
            assert len(plans) == 1, f"Should have exactly 1 plan, got {len(plans)}"
            
            plan = plans[0]
            
            # Verify all deployments are loaded
            assert len(plan.deployments) == num_deployments, \
                f"Plan should have {num_deployments} deployments, got {len(plan.deployments)}"
            
            # Property verification: Check that deployments are ordered by created_at descending
            for i in range(len(plan.deployments) - 1):
                current_timestamp = plan.deployments[i].created_at
                next_timestamp = plan.deployments[i + 1].created_at
                
                assert current_timestamp >= next_timestamp, \
                    f"Deployment at index {i} has timestamp {current_timestamp}, " \
                    f"but deployment at index {i+1} has timestamp {next_timestamp}. " \
                    f"Deployments should be ordered by created_at descending (newest first)."
            
            # Additional verification: The first deployment should have the maximum timestamp
            max_timestamp = max(deployment_timestamps)
            assert plan.deployments[0].created_at == max_timestamp, \
                f"First deployment should have the maximum timestamp {max_timestamp}, " \
                f"but has {plan.deployments[0].created_at}"
            
            # Additional verification: The last deployment should have the minimum timestamp
            min_timestamp = min(deployment_timestamps)
            assert plan.deployments[-1].created_at == min_timestamp, \
                f"Last deployment should have the minimum timestamp {min_timestamp}, " \
                f"but has {plan.deployments[-1].created_at}"
            
            # Verify the ordering matches a manual sort
            expected_order = sorted(deployment_timestamps, reverse=True)
            actual_order = [d.created_at for d in plan.deployments]
            
            assert actual_order == expected_order, \
                f"Deployment order does not match expected descending order. " \
                f"Expected: {expected_order}, Got: {actual_order}"
        finally:
            # Clean up
            await db_session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_deployments=st.integers(min_value=1, max_value=10),
    seed=st.integers(min_value=0, max_value=1000000)
)
async def test_property_deployment_response_fields(
    num_deployments: int,
    seed: int
):
    """
    # Feature: deployment-history, Property 8: Deployment Response Fields
    
    Property: For any Deployment returned by the get_user_plans_with_deployments method,
    the response object should include the fields: id, status, created_at, updated_at,
    completed_at, and error_message.
    
    This test verifies:
    1. All required fields are present in each deployment object
    2. Fields have the correct types (id is UUID, timestamps are datetime, etc.)
    3. This holds true across deployments with different statuses and field values
    """
    # Create database session for this test iteration
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create a test user
            user_id = f"test-user-prop8-{uuid.uuid4()}"
            email = f"user-prop8-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create a TerraformPlan
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements=f"Requirements for response fields test - seed {seed}",
                structured_requirements={"resources": ["ec2", "s3"]},
                s3_prefix=f"terraform/{user_id}/{uuid.uuid4()}/",
                status="completed"
            )
            db_session.add(plan)
            await db_session.flush()
            
            # Generate random deployments with various field combinations
            import random
            random.seed(seed)
            
            all_statuses = [
                DeploymentStatus.SUCCESS,
                DeploymentStatus.FAILED,
                DeploymentStatus.RUNNING,
                DeploymentStatus.STARTED,
                DeploymentStatus.DESTROYED,
                DeploymentStatus.DESTROY_FAILED
            ]
            
            base_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            
            for i in range(num_deployments):
                status = all_statuses[i % len(all_statuses)]
                
                # Create deployment with random field values
                created_at = base_timestamp.replace(hour=(base_timestamp.hour + i) % 24)
                updated_at = created_at.replace(minute=(created_at.minute + random.randint(1, 30)) % 60)
                
                # completed_at is set for completed statuses, None for in-progress
                completed_at = None
                if status in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, 
                             DeploymentStatus.DESTROYED, DeploymentStatus.DESTROY_FAILED]:
                    completed_at = updated_at.replace(second=(updated_at.second + random.randint(1, 30)) % 60)
                
                # error_message is set for failed statuses, None otherwise
                error_message = None
                if status in [DeploymentStatus.FAILED, DeploymentStatus.DESTROY_FAILED]:
                    error_message = f"Random error message {i} - seed {seed}"
                
                deployment = Deployment(
                    user_id=user_id,
                    terraform_plan_id=plan.id,
                    status=status,
                    created_at=created_at,
                    updated_at=updated_at,
                    completed_at=completed_at,
                    error_message=error_message
                )
                db_session.add(deployment)
            
            await db_session.commit()
            
            # Create repository instance and fetch plans with deployments
            plan_repo = TerraformPlanRepository(db_session)
            plans = await plan_repo.get_user_plans_with_deployments(user_id)
            
            # Verify we got the plan
            assert len(plans) == 1, f"Should have exactly 1 plan, got {len(plans)}"
            
            plan = plans[0]
            
            # Verify all deployments are loaded
            assert len(plan.deployments) == num_deployments, \
                f"Plan should have {num_deployments} deployments, got {len(plan.deployments)}"
            
            # Property verification: Check that all required fields are present in each deployment
            required_fields = ['id', 'status', 'created_at', 'updated_at', 'completed_at', 'error_message']
            
            for i, deployment in enumerate(plan.deployments):
                # Verify all required fields exist
                for field in required_fields:
                    assert hasattr(deployment, field), \
                        f"Deployment {i} is missing required field '{field}'"
                
                # Verify field types and values
                assert deployment.id is not None, \
                    f"Deployment {i} should have a non-null id"
                assert isinstance(deployment.id, uuid.UUID), \
                    f"Deployment {i} id should be a UUID, got {type(deployment.id)}"
                
                assert deployment.status is not None, \
                    f"Deployment {i} should have a non-null status"
                assert isinstance(deployment.status, DeploymentStatus), \
                    f"Deployment {i} status should be a DeploymentStatus enum, got {type(deployment.status)}"
                
                assert deployment.created_at is not None, \
                    f"Deployment {i} should have a non-null created_at"
                assert isinstance(deployment.created_at, datetime), \
                    f"Deployment {i} created_at should be a datetime, got {type(deployment.created_at)}"
                
                assert deployment.updated_at is not None, \
                    f"Deployment {i} should have a non-null updated_at"
                assert isinstance(deployment.updated_at, datetime), \
                    f"Deployment {i} updated_at should be a datetime, got {type(deployment.updated_at)}"
                
                # completed_at can be None for in-progress deployments
                if deployment.completed_at is not None:
                    assert isinstance(deployment.completed_at, datetime), \
                        f"Deployment {i} completed_at should be a datetime or None, got {type(deployment.completed_at)}"
                
                # error_message can be None for successful deployments
                if deployment.error_message is not None:
                    assert isinstance(deployment.error_message, str), \
                        f"Deployment {i} error_message should be a string or None, got {type(deployment.error_message)}"
                
                # Verify logical consistency of field values
                assert deployment.updated_at >= deployment.created_at, \
                    f"Deployment {i} updated_at should be >= created_at"
                
                if deployment.completed_at is not None:
                    assert deployment.completed_at >= deployment.created_at, \
                        f"Deployment {i} completed_at should be >= created_at"
        finally:
            # Clean up
            await db_session.rollback()
            await engine.dispose()
