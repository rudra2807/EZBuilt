"""
Property-based tests for Terraform execution error handling.

This test validates:
- Property 14: Error Status on Terraform Command Failure
- Property 15: Error Status on Unexpected Exceptions

Property 14: For any deployment, when any Terraform command (init, plan, apply) fails,
the deployment status should be updated to "failed" with the stderr output stored as
the error message.

Property 15: For any deployment, when an unexpected exception occurs during execution,
the deployment status should be updated to "failed" with the exception message stored.
"""

import pytest
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.deployment_service import execute_terraform_apply, execute_terraform_destroy
from src.database.models import DeploymentStatus


# ============================================================================
# Property 14: Error Status on Terraform Command Failure
# ============================================================================


@st.composite
def terraform_command_failure(draw):
    """
    Generate Terraform command failure scenarios.
    
    Returns a tuple of (command_name, error_message)
    where command_name is one of: 'init', 'plan', 'apply'
    """
    commands = ['init', 'plan', 'apply']
    command = draw(st.sampled_from(commands))
    
    # Generate realistic Terraform error messages
    error_templates = [
        "Error: Failed to install provider",
        "Error: Invalid configuration",
        "Error: Resource creation failed",
        "Error: Provider not found",
        "Error: Authentication failed",
        "Error: Insufficient permissions",
        "Error: Resource already exists",
        "Error: Invalid resource type",
        "Error: Missing required argument",
        "Error: Timeout waiting for resource"
    ]
    
    error_msg = draw(st.sampled_from(error_templates))
    
    # Optionally add ANSI color codes
    if draw(st.booleans()):
        error_msg = f"\x1B[31m{error_msg}\x1B[0m"
    
    return (command, error_msg)


@pytest.mark.asyncio
@given(failure=terraform_command_failure())
@settings(max_examples=100)
async def test_property_terraform_command_failure_apply(failure):
    """
    Property 14: Error Status on Terraform Command Failure (Apply)
    
    For any deployment, when any Terraform command (init, plan, apply) fails,
    the deployment status should be updated to "failed" with the stderr output
    stored as the error message.
    """
    command_name, error_message = failure
    
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = f"user_{uuid.uuid4()}/plan_{uuid.uuid4()}/v1/"
    role_arn = f"arn:aws:iam::{uuid.uuid4().hex[:12]}:role/TestRole"
    external_id = f"external-{uuid.uuid4()}"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Setup successful S3 download
        mock_download.return_value = ['main.tf', 'variables.tf']
        
        # Setup successful role assumption
        mock_assume.return_value = {
            'AccessKeyId': 'test-key-id',
            'SecretAccessKey': 'test-secret-key',
            'SessionToken': 'test-session-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Configure mock based on which command fails
        if command_name == 'init':
            # Init fails immediately
            mock_subprocess.return_value = MagicMock(
                returncode=1,
                stdout='',
                stderr=error_message
            )
        elif command_name == 'plan':
            # Init succeeds, plan fails
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                MagicMock(returncode=1, stdout='', stderr=error_message)    # plan
            ]
        elif command_name == 'apply':
            # Init and plan succeed, apply fails
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
                MagicMock(returncode=1, stdout='', stderr=error_message)    # apply
            ]
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property 1: Status should be updated to FAILED
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id, "Deployment ID should match"
        assert final_call[0][1] == DeploymentStatus.FAILED, \
            f"Status should be FAILED when {command_name} fails"
        
        # Property 2: Error message should be stored
        assert 'error_message' in final_call[1], "Error message should be provided"
        stored_error = final_call[1]['error_message']
        assert stored_error is not None, "Error message should not be None"
        assert len(stored_error) > 0, "Error message should not be empty"
        
        # Property 3: Error message should contain the original error text (without ANSI codes)
        # Strip ANSI codes from original error for comparison
        clean_error = error_message.replace('\x1B[31m', '').replace('\x1B[0m', '')
        assert clean_error in stored_error or stored_error in clean_error, \
            f"Stored error should contain original error text"
        
        # Property 4: Error message should not contain ANSI codes
        assert '\x1B' not in stored_error, "Error message should not contain ANSI escape codes"
        
        # Cleanup
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
@given(error_message=st.text(min_size=1, max_size=200))
@settings(max_examples=100)
async def test_property_terraform_destroy_failure(error_message):
    """
    Property 14: Error Status on Terraform Command Failure (Destroy)
    
    For any deployment, when terraform destroy fails, the deployment status
    should be updated to "destroy_failed" with the stderr output stored as
    the error message.
    """
    deployment_id = uuid.uuid4()
    role_arn = f"arn:aws:iam::{uuid.uuid4().hex[:12]}:role/TestRole"
    external_id = f"external-{uuid.uuid4()}"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess:
        
        MockRepo.return_value = mock_repo
        
        # Setup successful role assumption
        mock_assume.return_value = {
            'AccessKeyId': 'test-key-id',
            'SecretAccessKey': 'test-secret-key',
            'SessionToken': 'test-session-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Simulate terraform destroy failure
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr=error_message
        )
        
        # Execute the destroy
        await execute_terraform_destroy(
            deployment_id=deployment_id,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property 1: Status should be updated to DESTROY_FAILED
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id, "Deployment ID should match"
        assert final_call[0][1] == DeploymentStatus.DESTROY_FAILED, \
            "Status should be DESTROY_FAILED when destroy fails"
        
        # Property 2: Error message should be stored
        assert 'error_message' in final_call[1], "Error message should be provided"
        stored_error = final_call[1]['error_message']
        assert stored_error is not None, "Error message should not be None"
        
        # Property 3: Error message should contain reference to destroy failure
        assert 'Destroy failed' in stored_error, \
            "Error message should indicate destroy failure"
        
        # Cleanup
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)


# ============================================================================
# Property 15: Error Status on Unexpected Exceptions
# ============================================================================


@st.composite
def exception_scenario(draw):
    """
    Generate exception scenarios with different exception types and messages.
    
    Returns a tuple of (exception_type, exception_message, failure_point)
    where failure_point is one of: 's3_download', 'role_assumption', 'subprocess'
    """
    exception_types = [
        RuntimeError,
        ValueError,
        ConnectionError,
        TimeoutError,
        OSError
    ]
    
    exception_type = draw(st.sampled_from(exception_types))
    
    # Generate realistic exception messages
    message_templates = [
        "Database connection lost",
        "Network timeout occurred",
        "Permission denied",
        "Resource not available",
        "Invalid state transition",
        "Configuration error",
        "Service unavailable",
        "Authentication failed",
        "Rate limit exceeded",
        "Internal server error"
    ]
    
    exception_message = draw(st.sampled_from(message_templates))
    
    failure_points = ['s3_download', 'role_assumption', 'subprocess']
    failure_point = draw(st.sampled_from(failure_points))
    
    return (exception_type, exception_message, failure_point)


@pytest.mark.asyncio
@given(scenario=exception_scenario())
@settings(max_examples=100)
async def test_property_unexpected_exception_apply(scenario):
    """
    Property 15: Error Status on Unexpected Exceptions (Apply)
    
    For any deployment, when an unexpected exception occurs during execution,
    the deployment status should be updated to "failed" with the exception
    message stored.
    """
    exception_type, exception_message, failure_point = scenario
    
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = f"user_{uuid.uuid4()}/plan_{uuid.uuid4()}/v1/"
    role_arn = f"arn:aws:iam::{uuid.uuid4().hex[:12]}:role/TestRole"
    external_id = f"external-{uuid.uuid4()}"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Configure mock to raise exception at specified failure point
        if failure_point == 's3_download':
            mock_download.side_effect = exception_type(exception_message)
        elif failure_point == 'role_assumption':
            mock_download.return_value = ['main.tf']
            mock_assume.side_effect = exception_type(exception_message)
        elif failure_point == 'subprocess':
            mock_download.return_value = ['main.tf']
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            # Create temp directory for subprocess scenario
            os.makedirs(tmp_dir, exist_ok=True)
            mock_subprocess.side_effect = exception_type(exception_message)
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property 1: Status should be updated to FAILED
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id, "Deployment ID should match"
        assert final_call[0][1] == DeploymentStatus.FAILED, \
            f"Status should be FAILED when unexpected {exception_type.__name__} occurs"
        
        # Property 2: Error message should be stored
        assert 'error_message' in final_call[1], "Error message should be provided"
        stored_error = final_call[1]['error_message']
        assert stored_error is not None, "Error message should not be None"
        assert len(stored_error) > 0, "Error message should not be empty"
        
        # Property 3: Error message should indicate unexpected error
        assert 'Unexpected error' in stored_error, \
            "Error message should indicate unexpected error"
        
        # Property 4: Error message should contain the exception message
        assert exception_message in stored_error, \
            f"Error message should contain original exception message: {exception_message}"
        
        # Cleanup
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
@given(scenario=exception_scenario())
@settings(max_examples=100)
async def test_property_unexpected_exception_destroy(scenario):
    """
    Property 15: Error Status on Unexpected Exceptions (Destroy)
    
    For any deployment, when an unexpected exception occurs during destroy,
    the deployment status should be updated to "destroy_failed" with the
    exception message stored.
    """
    exception_type, exception_message, failure_point = scenario
    
    deployment_id = uuid.uuid4()
    role_arn = f"arn:aws:iam::{uuid.uuid4().hex[:12]}:role/TestRole"
    external_id = f"external-{uuid.uuid4()}"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess:
        
        MockRepo.return_value = mock_repo
        
        # Configure mock to raise exception at specified failure point
        if failure_point in ['s3_download', 'role_assumption']:
            # For destroy, both s3_download and role_assumption map to role_assumption
            mock_assume.side_effect = exception_type(exception_message)
        elif failure_point == 'subprocess':
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            # Create temp directory for subprocess scenario
            os.makedirs(tmp_dir, exist_ok=True)
            mock_subprocess.side_effect = exception_type(exception_message)
        
        # Execute the destroy
        await execute_terraform_destroy(
            deployment_id=deployment_id,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Property 1: Status should be updated to DESTROY_FAILED
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id, "Deployment ID should match"
        assert final_call[0][1] == DeploymentStatus.DESTROY_FAILED, \
            f"Status should be DESTROY_FAILED when unexpected {exception_type.__name__} occurs"
        
        # Property 2: Error message should be stored
        assert 'error_message' in final_call[1], "Error message should be provided"
        stored_error = final_call[1]['error_message']
        assert stored_error is not None, "Error message should not be None"
        assert len(stored_error) > 0, "Error message should not be empty"
        
        # Property 3: Error message should indicate unexpected error
        assert 'Unexpected error' in stored_error, \
            "Error message should indicate unexpected error"
        
        # Property 4: Error message should contain the exception message
        assert exception_message in stored_error, \
            f"Error message should contain original exception message: {exception_message}"
        
        # Cleanup
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)
