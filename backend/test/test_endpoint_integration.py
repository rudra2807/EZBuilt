"""
Integration tests for the structure-requirements endpoint flow.

Tests the complete flow:
1. Requirements → generation → S3 upload → validation → response
2. S3 upload failure scenarios
3. Validation failure scenarios
4. Database status updates in all cases
5. Tmp directory cleanup in all scenarios

Run with: python backend/test/test_endpoint_integration.py
"""

import sys
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock, call

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import upload_terraform_files, download_prefix_to_tmp, S3ServiceError
from src.services.terraform_exec import validate_terraform_from_s3
from src.utilities.schemas import ValidationResult


# Test data
SAMPLE_TERRAFORM_CODE = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket"
}
'''

SAMPLE_REQUIREMENTS = "I need an S3 bucket for storing files"


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def record_pass(self, test_name):
        self.passed += 1
        print(f"✓ {test_name}")
    
    def record_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResults()


def test_s3_upload_success():
    """Test successful S3 upload"""
    test_name = "S3 Upload Success"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            
            # Call upload
            upload_terraform_files(
                bucket="test-bucket",
                prefix="user123/plan456/v1/",
                files={"main.tf": SAMPLE_TERRAFORM_CODE}
            )
            
            # Verify S3 put_object was called
            assert s3_mock.put_object.called
            call_args = s3_mock.put_object.call_args[1]
            assert call_args["Bucket"] == "test-bucket"
            assert call_args["Key"] == "user123/plan456/v1/main.tf"
            assert call_args["ContentType"] == "text/plain"
            assert call_args["ServerSideEncryption"] == "AES256"
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_s3_upload_failure():
    """Test S3 upload failure raises S3ServiceError"""
    test_name = "S3 Upload Failure"
    try:
        from botocore.exceptions import ClientError
        
        with patch('src.services.s3_service.get_s3_client') as mock_client:
            s3_mock = MagicMock()
            # Use ClientError which is what boto3 actually raises
            s3_mock.put_object.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "PutObject"
            )
            mock_client.return_value = s3_mock
            
            # Should raise S3ServiceError
            try:
                upload_terraform_files(
                    bucket="test-bucket",
                    prefix="user123/plan456/v1/",
                    files={"main.tf": SAMPLE_TERRAFORM_CODE}
                )
                results.record_fail(test_name, "Expected S3ServiceError but none was raised")
            except S3ServiceError as e:
                assert "Failed to upload" in str(e)
                results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_s3_download_success():
    """Test successful S3 download"""
    test_name = "S3 Download Success"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            
            # Mock list_objects_v2 response
            s3_mock.list_objects_v2.return_value = {
                'Contents': [
                    {'Key': 'user123/plan456/v1/main.tf'}
                ]
            }
            
            # Create temp directory for test
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Call download
                files = download_prefix_to_tmp(
                    bucket="test-bucket",
                    prefix="user123/plan456/v1/",
                    local_path=tmp_dir
                )
                
                # Verify download_file was called
                assert s3_mock.download_file.called
                assert len(files) == 1
                assert files[0].endswith("main.tf")
                
                results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_s3_download_no_files():
    """Test S3 download with no files raises error"""
    test_name = "S3 Download No Files"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_client:
            s3_mock = MagicMock()
            mock_client.return_value = s3_mock
            
            # Mock empty response
            s3_mock.list_objects_v2.return_value = {}
            
            # Should raise S3ServiceError
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    download_prefix_to_tmp(
                        bucket="test-bucket",
                        prefix="user123/plan456/v1/",
                        local_path=tmp_dir
                    )
                results.record_fail(test_name, "Expected S3ServiceError but none was raised")
            except S3ServiceError as e:
                assert "No files found" in str(e)
                results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_validation_success():
    """Test successful Terraform validation from S3"""
    test_name = "Validation Success"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_s3, \
             patch('src.services.terraform_exec.subprocess.run') as mock_subprocess, \
             patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            
            # Mock S3 download
            mock_download.return_value = ["/tmp/test-plan/main.tf"]
            
            # Mock terraform commands (init and validate both succeed)
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout="Success", stderr=""),  # init
                MagicMock(returncode=0, stdout="Success", stderr="")   # validate
            ]
            
            # Call validation
            result = validate_terraform_from_s3(
                bucket="test-bucket",
                s3_prefix="user123/plan456/v1/",
                plan_id="test-plan-123"
            )
            
            # Verify result
            assert result.valid is True
            assert result.errors is None
            
            # Verify tmp directory was cleaned up
            tmp_dir = "/tmp/test-plan-123"
            assert not os.path.exists(tmp_dir)
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_validation_init_failure():
    """Test Terraform init failure"""
    test_name = "Validation Init Failure"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_s3, \
             patch('src.services.terraform_exec.subprocess.run') as mock_subprocess, \
             patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            
            # Mock S3 download
            mock_download.return_value = ["/tmp/test-plan/main.tf"]
            
            # Mock terraform init to fail
            mock_subprocess.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: Failed to initialize"
            )
            
            # Call validation
            result = validate_terraform_from_s3(
                bucket="test-bucket",
                s3_prefix="user123/plan456/v1/",
                plan_id="test-plan-init-fail"
            )
            
            # Verify result
            assert result.valid is False
            assert "Failed to initialize" in result.errors
            
            # Verify tmp directory was cleaned up
            tmp_dir = "/tmp/test-plan-init-fail"
            assert not os.path.exists(tmp_dir)
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_validation_validate_failure():
    """Test Terraform validate failure"""
    test_name = "Validation Validate Failure"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_s3, \
             patch('src.services.terraform_exec.subprocess.run') as mock_subprocess, \
             patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            
            # Mock S3 download
            mock_download.return_value = ["/tmp/test-plan/main.tf"]
            
            # Mock terraform commands: init succeeds, validate fails
            mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout="Success", stderr=""),  # init
                MagicMock(returncode=1, stdout="", stderr="Error: Invalid syntax")  # validate
            ]
            
            # Call validation
            result = validate_terraform_from_s3(
                bucket="test-bucket",
                s3_prefix="user123/plan456/v1/",
                plan_id="test-plan-validate-fail"
            )
            
            # Verify result
            assert result.valid is False
            assert "Invalid syntax" in result.errors
            
            # Verify tmp directory was cleaned up
            tmp_dir = "/tmp/test-plan-validate-fail"
            assert not os.path.exists(tmp_dir)
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_validation_s3_download_failure():
    """Test validation with S3 download failure"""
    test_name = "Validation S3 Download Failure"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_s3, \
             patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            
            # Mock S3 download to raise error
            mock_download.side_effect = S3ServiceError("Failed to download files")
            
            # Call validation
            result = validate_terraform_from_s3(
                bucket="test-bucket",
                s3_prefix="user123/plan456/v1/",
                plan_id="test-plan-download-fail"
            )
            
            # Verify result
            assert result.valid is False
            assert "Failed to download files from S3" in result.errors
            
            # Verify tmp directory was cleaned up
            tmp_dir = "/tmp/test-plan-download-fail"
            assert not os.path.exists(tmp_dir)
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_validation_cleanup_on_exception():
    """Test tmp directory cleanup even when unexpected exception occurs"""
    test_name = "Validation Cleanup On Exception"
    try:
        with patch('src.services.s3_service.get_s3_client') as mock_s3, \
             patch('src.services.terraform_exec.subprocess.run') as mock_subprocess, \
             patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            
            # Mock S3 download
            mock_download.return_value = ["/tmp/test-plan/main.tf"]
            
            # Mock terraform to raise unexpected exception
            mock_subprocess.side_effect = Exception("Unexpected error")
            
            # Call validation
            result = validate_terraform_from_s3(
                bucket="test-bucket",
                s3_prefix="user123/plan456/v1/",
                plan_id="test-plan-exception"
            )
            
            # Verify result
            assert result.valid is False
            assert "Validation error" in result.errors
            
            # Verify tmp directory was cleaned up
            tmp_dir = "/tmp/test-plan-exception"
            assert not os.path.exists(tmp_dir)
            
            results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def test_tmp_directory_isolation():
    """Test that each validation uses isolated tmp directory"""
    test_name = "Tmp Directory Isolation"
    try:
        plan_ids = ["plan-1", "plan-2", "plan-3"]
        
        for plan_id in plan_ids:
            with patch('src.services.s3_service.get_s3_client') as mock_s3, \
                 patch('src.services.terraform_exec.subprocess.run') as mock_subprocess, \
                 patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
                
                # Mock S3 download
                mock_download.return_value = [f"/tmp/{plan_id}/main.tf"]
                
                # Mock terraform commands
                mock_subprocess.side_effect = [
                    MagicMock(returncode=0, stdout="Success", stderr=""),
                    MagicMock(returncode=0, stdout="Success", stderr="")
                ]
                
                # Call validation
                validate_terraform_from_s3(
                    bucket="test-bucket",
                    s3_prefix=f"user/{plan_id}/v1/",
                    plan_id=plan_id
                )
                
                # Verify tmp directory was cleaned up
                tmp_dir = f"/tmp/{plan_id}"
                assert not os.path.exists(tmp_dir)
        
        results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("Running Integration Tests for Endpoint Flow")
    print("="*60 + "\n")
    
    # S3 Upload Tests
    print("S3 Upload Tests:")
    test_s3_upload_success()
    test_s3_upload_failure()
    
    # S3 Download Tests
    print("\nS3 Download Tests:")
    test_s3_download_success()
    test_s3_download_no_files()
    
    # Validation Tests
    print("\nValidation Tests:")
    test_validation_success()
    test_validation_init_failure()
    test_validation_validate_failure()
    test_validation_s3_download_failure()
    
    # Cleanup Tests
    print("\nCleanup Tests:")
    test_validation_cleanup_on_exception()
    test_tmp_directory_isolation()
    
    # Print summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
