"""
Property-based tests for deployment service functions.

This test validates:
- Property 16: ANSI Code Stripping
- Property 17: Temporary Directory Cleanup

Property 16: For any error message or output containing ANSI color codes,
when stored in the database, all ANSI escape sequences should be removed,
leaving only plain text.

Property 17: For any deployment execution (apply or destroy), when the operation
completes (success or failure), the temporary directory created for Terraform
execution should be removed from the filesystem.
"""

import pytest
import os
import sys
import uuid
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.deployment_service import strip_ansi_codes, execute_terraform_apply, execute_terraform_destroy
from src.database.models import DeploymentStatus


# Strategy for generating ANSI escape sequences
@st.composite
def ansi_codes(draw):
    """Generate valid ANSI escape sequences"""
    # Common ANSI color codes
    color_codes = [
        "\x1B[0m",    # Reset
        "\x1B[1m",    # Bold
        "\x1B[2m",    # Dim
        "\x1B[3m",    # Italic
        "\x1B[4m",    # Underline
        "\x1B[30m",   # Black
        "\x1B[31m",   # Red
        "\x1B[32m",   # Green
        "\x1B[33m",   # Yellow
        "\x1B[34m",   # Blue
        "\x1B[35m",   # Magenta
        "\x1B[36m",   # Cyan
        "\x1B[37m",   # White
        "\x1B[90m",   # Bright Black
        "\x1B[91m",   # Bright Red
        "\x1B[92m",   # Bright Green
        "\x1B[93m",   # Bright Yellow
        "\x1B[94m",   # Bright Blue
        "\x1B[95m",   # Bright Magenta
        "\x1B[96m",   # Bright Cyan
        "\x1B[97m",   # Bright White
        "\x1B[40m",   # Background Black
        "\x1B[41m",   # Background Red
        "\x1B[42m",   # Background Green
        "\x1B[43m",   # Background Yellow
        "\x1B[44m",   # Background Blue
        "\x1B[45m",   # Background Magenta
        "\x1B[46m",   # Background Cyan
        "\x1B[47m",   # Background White
    ]
    return draw(st.sampled_from(color_codes))


@st.composite
def text_with_ansi(draw):
    """Generate text with ANSI codes embedded"""
    # Generate plain text parts
    num_parts = draw(st.integers(min_value=1, max_value=5))
    parts = []
    
    for _ in range(num_parts):
        # Add plain text
        plain_text = draw(st.text(
            alphabet=st.characters(
                blacklist_categories=('Cs',),  # Exclude surrogates
                blacklist_characters='\x1B'     # Exclude ESC character
            ),
            min_size=0,
            max_size=50
        ))
        parts.append(plain_text)
        
        # Optionally add ANSI code
        if draw(st.booleans()):
            ansi = draw(ansi_codes())
            parts.append(ansi)
    
    return ''.join(parts)


@pytest.mark.asyncio
@given(text=text_with_ansi())
@settings(max_examples=100)
async def test_property_ansi_code_stripping(text):
    """
    Property 16: ANSI Code Stripping
    
    For any text containing ANSI escape sequences, when strip_ansi_codes is called,
    the result should contain no ANSI escape sequences.
    """
    # Apply the strip_ansi_codes function
    result = strip_ansi_codes(text)
    
    # Property 1: Result should not contain any ANSI escape sequences
    # ANSI codes start with ESC character (\x1B)
    assert '\x1B' not in result, f"Result should not contain ESC character: {repr(result)}"
    
    # Property 2: Result should not contain CSI sequences (ESC[...)
    assert '\x1B[' not in result, f"Result should not contain CSI sequences: {repr(result)}"
    
    # Property 3: If input has no ANSI codes, output should be identical
    if '\x1B' not in text:
        assert result == text, "Text without ANSI codes should remain unchanged"


@pytest.mark.asyncio
async def test_ansi_stripping_specific_examples():
    """
    Unit tests for specific ANSI code stripping examples.
    
    These tests verify common Terraform output patterns.
    """
    # Test 1: Simple color code
    assert strip_ansi_codes("\x1B[32mSuccess\x1B[0m") == "Success"
    
    # Test 2: Multiple color codes
    assert strip_ansi_codes("\x1B[31mError:\x1B[0m \x1B[33mWarning\x1B[0m") == "Error: Warning"
    
    # Test 3: Bold text
    assert strip_ansi_codes("\x1B[1mBold text\x1B[0m") == "Bold text"
    
    # Test 4: Complex Terraform-like output
    terraform_output = "\x1B[0m\x1B[1mTerraform will perform the following actions:\x1B[0m\n\x1B[32m+ create\x1B[0m"
    expected = "Terraform will perform the following actions:\n+ create"
    assert strip_ansi_codes(terraform_output) == expected
    
    # Test 5: Empty string
    assert strip_ansi_codes("") == ""
    
    # Test 6: No ANSI codes
    plain_text = "This is plain text without any codes"
    assert strip_ansi_codes(plain_text) == plain_text
    
    # Test 7: Only ANSI codes
    assert strip_ansi_codes("\x1B[31m\x1B[0m") == ""
    
    # Test 8: Background colors
    assert strip_ansi_codes("\x1B[41mRed background\x1B[0m") == "Red background"
    
    # Test 9: Bright colors
    assert strip_ansi_codes("\x1B[91mBright red\x1B[0m") == "Bright red"
    
    # Test 10: Multiple lines with ANSI codes
    multiline = "\x1B[32mLine 1\x1B[0m\n\x1B[33mLine 2\x1B[0m\n\x1B[31mLine 3\x1B[0m"
    expected_multiline = "Line 1\nLine 2\nLine 3"
    assert strip_ansi_codes(multiline) == expected_multiline


# ============================================================================
# Property 17: Temporary Directory Cleanup
# ============================================================================


@st.composite
def deployment_scenario(draw):
    """
    Generate deployment scenarios with different outcomes.
    
    Returns a tuple of (scenario_type, should_fail_at_stage)
    where scenario_type is one of: 'success', 's3_failure', 'init_failure', 
    'plan_failure', 'apply_failure', 'exception'
    """
    scenario_types = [
        'success',
        's3_failure',
        'init_failure',
        'plan_failure',
        'apply_failure',
        'exception'
    ]
    return draw(st.sampled_from(scenario_types))


@pytest.mark.asyncio
@given(scenario=deployment_scenario())
@settings(max_examples=100)
async def test_property_temporary_directory_cleanup_apply(scenario):
    """
    Property 17: Temporary Directory Cleanup (Apply)
    
    For any deployment execution (apply), when the operation completes
    (success or failure), the temporary directory created for Terraform
    execution should be removed from the filesystem.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = f"user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    # Setup mocks based on scenario
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Create the temporary directory to simulate real execution
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Verify directory exists before execution
        assert os.path.exists(tmp_dir), f"Temp directory should exist before execution: {tmp_dir}"
        
        # Configure mocks based on scenario
        if scenario == 'success':
            mock_download.return_value = ['main.tf', 'variables.tf']
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            # Mock successful terraform commands
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
                MagicMock(returncode=0, stdout='Apply success', stderr='')  # apply
            ]
        
        elif scenario == 's3_failure':
            from src.services.s3_service import S3ServiceError
            mock_download.side_effect = S3ServiceError("S3 download failed")
        
        elif scenario == 'init_failure':
            mock_download.return_value = ['main.tf']
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            mock_subprocess.return_value = MagicMock(
                returncode=1,
                stdout='',
                stderr='Init failed: provider not found'
            )
        
        elif scenario == 'plan_failure':
            mock_download.return_value = ['main.tf']
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                MagicMock(returncode=1, stdout='', stderr='Plan failed: invalid config')  # plan
            ]
        
        elif scenario == 'apply_failure':
            mock_download.return_value = ['main.tf']
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
                MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
                MagicMock(returncode=1, stdout='', stderr='Apply failed: resource error')  # apply
            ]
        
        elif scenario == 'exception':
            mock_download.side_effect = Exception("Unexpected error occurred")
        
        # Execute the deployment
        try:
            await execute_terraform_apply(
                deployment_id=deployment_id,
                terraform_plan_id=terraform_plan_id,
                s3_prefix=s3_prefix,
                role_arn=role_arn,
                external_id=external_id,
                db=mock_db
            )
        except Exception:
            # Even if an exception is raised, cleanup should still happen
            pass
        
        # Property: Temporary directory should be cleaned up regardless of outcome
        assert not os.path.exists(tmp_dir), \
            f"Temporary directory should be cleaned up after {scenario}: {tmp_dir}"


@pytest.mark.asyncio
@given(scenario=deployment_scenario())
@settings(max_examples=100)
async def test_property_temporary_directory_cleanup_destroy(scenario):
    """
    Property 17: Temporary Directory Cleanup (Destroy)
    
    For any deployment execution (destroy), when the operation completes
    (success or failure), the temporary directory created for Terraform
    execution should be removed from the filesystem.
    """
    deployment_id = uuid.uuid4()
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    tmp_dir = f"/tmp/{deployment_id}"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    # Setup mocks based on scenario
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.assume_role') as mock_assume, \
         patch('src.services.deployment_service.subprocess.run') as mock_subprocess:
        
        MockRepo.return_value = mock_repo
        
        # Create the temporary directory to simulate real execution
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Verify directory exists before execution
        assert os.path.exists(tmp_dir), f"Temp directory should exist before execution: {tmp_dir}"
        
        # Configure mocks based on scenario
        if scenario == 'success':
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout='Destroy success',
                stderr=''
            )
        
        elif scenario in ['s3_failure', 'init_failure', 'plan_failure', 'apply_failure']:
            # For destroy, these scenarios translate to destroy failure
            mock_assume.return_value = {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
            mock_subprocess.return_value = MagicMock(
                returncode=1,
                stdout='',
                stderr='Destroy failed: resource not found'
            )
        
        elif scenario == 'exception':
            mock_assume.side_effect = Exception("Unexpected error occurred")
        
        # Execute the destroy
        try:
            await execute_terraform_destroy(
                deployment_id=deployment_id,
                role_arn=role_arn,
                external_id=external_id,
                db=mock_db
            )
        except Exception:
            # Even if an exception is raised, cleanup should still happen
            pass
        
        # Property: Temporary directory should be cleaned up regardless of outcome
        assert not os.path.exists(tmp_dir), \
            f"Temporary directory should be cleaned up after {scenario}: {tmp_dir}"


# ============================================================================
# Unit Tests for Deployment Service Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_s3_download_failure_handling():
    """
    Test S3 download failure handling.
    
    When S3 download fails with S3ServiceError, the deployment status
    should be updated to FAILED with the error message stored.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = "user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Simulate S3 download failure
        from src.services.s3_service import S3ServiceError
        mock_download.side_effect = S3ServiceError("Access denied to S3 bucket")
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Verify status was updated to RUNNING first
        assert mock_repo.update_status.call_count >= 2
        first_call = mock_repo.update_status.call_args_list[0]
        assert first_call[0][0] == deployment_id
        assert first_call[0][1] == DeploymentStatus.RUNNING
        
        # Verify status was updated to FAILED with error message
        second_call = mock_repo.update_status.call_args_list[1]
        assert second_call[0][0] == deployment_id
        assert second_call[0][1] == DeploymentStatus.FAILED
        assert second_call[1]['error_message'] == "S3 download failed: Access denied to S3 bucket"


@pytest.mark.asyncio
async def test_terraform_init_failure_handling():
    """
    Test Terraform init failure handling.
    
    When terraform init fails, the deployment status should be updated
    to FAILED with the stderr output stored as error message.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = "user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
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
            'AccessKeyId': 'test-key',
            'SecretAccessKey': 'test-secret',
            'SessionToken': 'test-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Simulate terraform init failure
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='\x1B[31mError: Failed to install provider\x1B[0m'
        )
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Verify status was updated to FAILED with error message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.FAILED
        assert 'Init failed' in final_call[1]['error_message']
        assert 'Failed to install provider' in final_call[1]['error_message']
        # Verify ANSI codes were stripped
        assert '\x1B' not in final_call[1]['error_message']


@pytest.mark.asyncio
async def test_terraform_plan_failure_handling():
    """
    Test Terraform plan failure handling.
    
    When terraform plan fails, the deployment status should be updated
    to FAILED with the stderr output stored as error message.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = "user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
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
        mock_download.return_value = ['main.tf']
        
        # Setup successful role assumption
        mock_assume.return_value = {
            'AccessKeyId': 'test-key',
            'SecretAccessKey': 'test-secret',
            'SessionToken': 'test-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Simulate successful init, failed plan
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
            MagicMock(returncode=1, stdout='', stderr='\x1B[33mError: Invalid configuration\x1B[0m')  # plan
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
        
        # Verify status was updated to FAILED with error message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.FAILED
        assert 'Plan failed' in final_call[1]['error_message']
        assert 'Invalid configuration' in final_call[1]['error_message']
        # Verify ANSI codes were stripped
        assert '\x1B' not in final_call[1]['error_message']


@pytest.mark.asyncio
async def test_terraform_apply_failure_handling():
    """
    Test Terraform apply failure handling.
    
    When terraform apply fails, the deployment status should be updated
    to FAILED with the stderr output stored as error message.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = "user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
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
        mock_download.return_value = ['main.tf']
        
        # Setup successful role assumption
        mock_assume.return_value = {
            'AccessKeyId': 'test-key',
            'SecretAccessKey': 'test-secret',
            'SessionToken': 'test-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Simulate successful init and plan, failed apply
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout='Init success', stderr=''),  # init
            MagicMock(returncode=0, stdout='Plan success', stderr=''),  # plan
            MagicMock(returncode=1, stdout='', stderr='\x1B[31mError: Resource creation failed\x1B[0m')  # apply
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
        
        # Verify status was updated to FAILED with error message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.FAILED
        assert 'Apply failed' in final_call[1]['error_message']
        assert 'Resource creation failed' in final_call[1]['error_message']
        # Verify ANSI codes were stripped
        assert '\x1B' not in final_call[1]['error_message']


@pytest.mark.asyncio
async def test_terraform_destroy_failure_handling():
    """
    Test Terraform destroy failure handling.
    
    When terraform destroy fails, the deployment status should be updated
    to DESTROY_FAILED with the stderr output stored as error message.
    """
    deployment_id = uuid.uuid4()
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
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
            'AccessKeyId': 'test-key',
            'SecretAccessKey': 'test-secret',
            'SessionToken': 'test-token'
        }
        
        # Create temp directory
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Simulate terraform destroy failure
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='\x1B[31mError: Resource still in use\x1B[0m'
        )
        
        # Execute the destroy
        await execute_terraform_destroy(
            deployment_id=deployment_id,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Verify status was updated to DESTROY_FAILED with error message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.DESTROY_FAILED
        assert 'Destroy failed' in final_call[1]['error_message']
        assert 'Resource still in use' in final_call[1]['error_message']
        # Verify ANSI codes were stripped
        assert '\x1B' not in final_call[1]['error_message']


@pytest.mark.asyncio
async def test_unexpected_exception_handling_apply():
    """
    Test unexpected exception handling during apply.
    
    When an unexpected exception occurs during deployment, the status
    should be updated to FAILED with the exception message stored.
    """
    deployment_id = uuid.uuid4()
    terraform_plan_id = uuid.uuid4()
    s3_prefix = "user123/plan456/v1/"
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.download_prefix_to_tmp') as mock_download, \
         patch.dict(os.environ, {'TERRAFORM_SOURCE_BUCKET': 'test-bucket'}):
        
        MockRepo.return_value = mock_repo
        
        # Simulate unexpected exception
        mock_download.side_effect = RuntimeError("Unexpected database connection error")
        
        # Execute the deployment
        await execute_terraform_apply(
            deployment_id=deployment_id,
            terraform_plan_id=terraform_plan_id,
            s3_prefix=s3_prefix,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Verify status was updated to FAILED with exception message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.FAILED
        assert 'Unexpected error' in final_call[1]['error_message']
        assert 'Unexpected database connection error' in final_call[1]['error_message']


@pytest.mark.asyncio
async def test_unexpected_exception_handling_destroy():
    """
    Test unexpected exception handling during destroy.
    
    When an unexpected exception occurs during destroy, the status
    should be updated to DESTROY_FAILED with the exception message stored.
    """
    deployment_id = uuid.uuid4()
    role_arn = "arn:aws:iam::123456789012:role/TestRole"
    external_id = "test-external-id"
    
    # Create mock database session and repository
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    
    with patch('src.services.deployment_service.DeploymentRepository') as MockRepo, \
         patch('src.services.deployment_service.assume_role') as mock_assume:
        
        MockRepo.return_value = mock_repo
        
        # Simulate unexpected exception
        mock_assume.side_effect = RuntimeError("AWS credentials expired")
        
        # Execute the destroy
        await execute_terraform_destroy(
            deployment_id=deployment_id,
            role_arn=role_arn,
            external_id=external_id,
            db=mock_db
        )
        
        # Verify status was updated to DESTROY_FAILED with exception message
        final_call = mock_repo.update_status.call_args_list[-1]
        assert final_call[0][0] == deployment_id
        assert final_call[0][1] == DeploymentStatus.DESTROY_FAILED
        assert 'Unexpected error' in final_call[1]['error_message']
        assert 'AWS credentials expired' in final_call[1]['error_message']
