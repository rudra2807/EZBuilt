"""
Property-based tests for S3 integration.

This test validates:
- Property 11: S3 Prefix Usage
- Property 12: S3 File Download Completeness
- Property 13: Error Status on S3 Failure

Property 11: For any deployment, when downloading Terraform files, the system
should use the s3_prefix value from the associated terraform_plan record.

Property 12: For any S3 prefix containing Terraform files, when downloading to
a temporary directory, all files under that prefix should be downloaded to the
local directory.

Property 13: For any deployment, when S3 download fails with an S3ServiceError,
the deployment status should be updated to "failed" with the error message stored.
"""

import pytest
import os
import sys
import uuid
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, call
from hypothesis import given, strategies as st, settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.deployment_service import execute_terraform_apply
from src.services.s3_service import download_prefix_to_tmp, S3ServiceError
from src.database.models import User, TerraformPlan, AWSIntegration, DeploymentStatus, IntegrationStatus
from src.database.repositories import DeploymentRepository


# Use local test database
DATABASE_URL = "postgresql+asyncpg://postgres:master@localhost:5432/ezbuilt_test"


# ============================================================================
# Property 11: S3 Prefix Usage
# ============================================================================


@st.composite
def s3_prefix_strategy(draw):
    """
    Generate valid S3 prefixes.
    
    Format: user_id/plan_id/version/
    """
    # Use only ASCII alphanumeric characters to avoid encoding issues
    user_part = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        min_size=5,
        max_size=20
    ))
    plan_part = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        min_size=5,
        max_size=20
    ))
    version = draw(st.sampled_from(['v1', 'v2', 'v3']))
    
    return f"{user_part}/{plan_part}/{version}/"


@pytest.mark.asyncio
@given(s3_prefix=s3_prefix_strategy())
@settings(max_examples=100, deadline=None)
async def test_property_s3_prefix_usage(s3_prefix):
    """
    Property 11: S3 Prefix Usage
    
    For any deployment, when downloading Terraform files, the system should
    use the s3_prefix value from the associated terraform_plan record.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Mock successful S3 download
        mock_download.return_value = ['main.tf', 'variables.tf']
        
        # Mock successful role assumption
        mock_assume.return_value = {
            'AccessKeyId': 'test-key',
            'SecretAccessKey': 'test-secret',
            'SessionToken': 'test-token'
        }
        
        # Mock successful Terraform commands
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
            MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
            MagicMock(returncode=0, stdout='Apply success', stderr='')  # apply
        ]
        
        # Execute the deployment with the specific s3_prefix
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property: The download_prefix_to_tmp function should be called with the exact s3_prefix
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        
        # Verify the s3_prefix argument matches what was passed to execute_terraform_apply
        assert call_args[0][1] == s3_prefix, \
            f"S3 prefix used for download ({call_args[0][1]}) should match terraform_plan s3_prefix ({s3_prefix})"
        
        # Verify bucket name is from environment
        assert call_args[0][0] == 'test-bucket', \
            "Bucket name should come from TERRAFORM_SOURCE_BUCKET environment variable"


# ============================================================================
# Property 12: S3 File Download Completeness
# ============================================================================


@st.composite
def s3_file_list_strategy(draw):
    """
    Generate a list of Terraform file names.
    
    Returns a list of filenames that might exist in an S3 prefix.
    """
    # Common Terraform files
    base_files = ['main.tf', 'variables.tf', 'outputs.tf', 'providers.tf']
    
    # Randomly select which base files to include (at least 1)
    num_files = draw(st.integers(min_value=1, max_value=len(base_files)))
    selected_files = draw(st.lists(
        st.sampled_from(base_files),
        min_size=num_files,
        max_size=num_files,
        unique=True
    ))
    
    # Optionally add module files
    has_modules = draw(st.booleans())
    if has_modules:
        # Use only ASCII lowercase letters for module names
        module_name = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz',
            min_size=3,
            max_size=10
        ))
        selected_files.append(f"modules/{module_name}/main.tf")
    
    return selected_files


@pytest.mark.asyncio
@given(
    s3_prefix=s3_prefix_strategy(),
    files=s3_file_list_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_s3_file_download_completeness(s3_prefix, files):
    """
    Property 12: S3 File Download Completeness
    
    For any S3 prefix containing Terraform files, when downloading to a
    temporary directory, all files under that prefix should be downloaded
    to the local directory.
    """
    bucket = "test-bucket"
    tmp_dir = tempfile.mkdtemp()
    
    try:
        # Mock S3 client
        mock_s3_client = MagicMock()
        
        # Create mock S3 response with all files
        mock_contents = []
        for filename in files:
            mock_contents.append({
                'Key': f"{s3_prefix}{filename}",
                'Size': 100
            })
        
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': mock_contents
        }
        
        # Mock download_file to create actual files
        def mock_download_file(bucket_name, key, local_path):
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            # Create the file with UTF-8 encoding
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(f"# Content of {key}")
        
        mock_s3_client.download_file.side_effect = mock_download_file
        
        # Patch get_s3_client to return our mock
        with patch('src.services.s3_service.get_s3_client', return_value=mock_s3_client):
            # Download files
            downloaded_files = download_prefix_to_tmp(bucket, s3_prefix, tmp_dir)
            
            # Property 1: Number of downloaded files should match number of files in S3
            assert len(downloaded_files) == len(files), \
                f"Should download all {len(files)} files, but downloaded {len(downloaded_files)}"
            
            # Property 2: All files should exist in the local directory
            for filename in files:
                expected_path = os.path.join(tmp_dir, filename)
                assert os.path.exists(expected_path), \
                    f"Downloaded file should exist at {expected_path}"
                
                # Verify file is in the returned list
                assert expected_path in downloaded_files, \
                    f"Downloaded file {expected_path} should be in returned list"
            
            # Property 3: download_file should be called for each file
            assert mock_s3_client.download_file.call_count == len(files), \
                f"download_file should be called {len(files)} times"
            
            # Property 4: All downloaded files should be under the tmp_dir
            for downloaded_file in downloaded_files:
                assert downloaded_file.startswith(tmp_dir), \
                    f"Downloaded file {downloaded_file} should be under {tmp_dir}"
    
    finally:
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


# ============================================================================
# Property 13: Error Status on S3 Failure
# ============================================================================


@st.composite
def s3_error_message_strategy(draw):
    """
    Generate realistic S3 error messages.
    """
    error_types = [
        "Access denied to S3 bucket",
        "Bucket does not exist",
        "Network timeout while accessing S3",
        "Invalid credentials for S3 access",
        "S3 service unavailable",
        "No files found under prefix",
        "Permission denied: s3:GetObject"
    ]
    return draw(st.sampled_from(error_types))


@pytest.mark.asyncio
@given(
    s3_prefix=s3_prefix_strategy(),
    error_message=s3_error_message_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_error_status_on_s3_failure(s3_prefix, error_message):
    """
    Property 13: Error Status on S3 Failure
    
    For any deployment, when S3 download fails with an S3ServiceError,
    the deployment status should be updated to "failed" with the error
    message stored.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Mock S3 download failure with the generated error message
        mock_download.side_effect = S3ServiceError(error_message)
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property 1: Status should be updated to RUNNING first
        assert mock_repo.update_status.call_count >= 2, \
            "Status should be updated at least twice (RUNNING, then FAILED)"
        
        first_call = mock_repo.update_status.call_args_list[0]
        assert first_call[0][0] == deployment_id, \
            "First status update should be for the correct deployment"
        assert first_call[0][1] == DeploymentStatus.RUNNING, \
            "First status update should set status to RUNNING"
        
        # Property 2: Final status should be FAILED
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id, \
            "Final status update should be for the correct deployment"
        assert final_call[0][1] == DeploymentStatus.FAILED, \
            "Final status should be FAILED when S3 download fails"
        
        # Property 3: Error message should be stored
        assert 'error_message' in final_call[1], \
            "Error message should be provided in status update"
        stored_error = final_call[1]['error_message']
        
        assert stored_error is not None, \
            "Error message should not be None"
        assert "S3 download failed" in stored_error, \
            "Error message should indicate S3 download failure"
        assert error_message in stored_error, \
            f"Error message should contain the original error: {error_message}"
        
        # Property 4: Output should not be set on failure
        assert final_call[1].get('output') is None, \
            "Output should be None when deployment fails"


# ============================================================================
# Integration Test: S3 Prefix Usage with Real Database
# ============================================================================


@pytest.mark.asyncio
async def test_s3_prefix_usage_integration():
    """
    Integration test verifying S3 prefix usage with real database.
    
    This test creates a real terraform_plan record with a specific s3_prefix
    and verifies that the deployment service uses that exact prefix when
    downloading files from S3.
    """
    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=None)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db_session:
        try:
            # Create test user
            user_id = f"test-user-{uuid.uuid4()}"
            email = f"user-{uuid.uuid4()}@example.com"
            
            user = User(user_id=user_id, email=email)
            db_session.add(user)
            await db_session.commit()
            
            # Create AWS integration
            aws_conn = AWSIntegration(
                user_id=user_id,
                external_id=f"ext-{uuid.uuid4()}",
                aws_account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                status=IntegrationStatus.CONNECTED
            )
            db_session.add(aws_conn)
            await db_session.commit()
            await db_session.refresh(aws_conn)
            
            # Create terraform plan with specific s3_prefix
            specific_prefix = f"terraform/{user_id}/{uuid.uuid4()}/v1/"
            plan = TerraformPlan(
                user_id=user_id,
                original_requirements="Test infrastructure",
                structured_requirements={"resources": ["ec2"]},
                s3_prefix=specific_prefix,
                status="completed"
            )
            db_session.add(plan)
            await db_session.commit()
            await db_session.refresh(plan)
            
            # Create deployment
            deployment_repo = DeploymentRepository(db_session)
            deployment = await deployment_repo.create(
                user_id=user_id,
                terraform_plan_id=plan.id,
                aws_connection_id=aws_conn.id
            )
            
            # Mock S3 and Terraform operations
            with patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
                 patch('src.services.deployment_service.assume_role') as mock_assume, \
                 patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
                 patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
                
                # Mock successful operations
                mock_download.return_value = ['main.tf']
                mock_assume.return_value = {
                    'AccessKeyId': 'test-key',
                    'SecretAccessKey': 'test-secret',
                    'SessionToken': 'test-token'
                }
                mock_subprocess.side_effect = [
                    MagicMock(returncode=0, stdout='Init', stderr=''),
                    MagicMock(returncode=0, stdout='Plan', stderr=''),
                    MagicMock(returncode=0, stdout='Apply', stderr='')
                ]
                
                # Execute deployment
                await execute_terraform_apply(
                    deployment_id=deployment.id,
                    terraform_plan_id=plan.id,
                    s3_prefix=plan.s3_prefix,
                    role_arn=aws_conn.role_arn,
                    external_id=aws_conn.external_id,
                    db=db_session
                )
                
                # Verify the exact s3_prefix from the plan was used
                mock_download.assert_called_once()
                call_args = mock_download.call_args
                
                assert call_args[0][1] == specific_prefix, \
                    f"Should use the exact s3_prefix from terraform_plan: {specific_prefix}"
        
        finally:
            await db_session.rollback()
    
    await engine.dispose()
