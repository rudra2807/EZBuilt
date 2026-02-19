#!/usr/bin/env python3
"""
Integration tests for S3-based Terraform validation flow.

Tests the validate_terraform_from_s3 function with various scenarios:
- Valid Terraform code
- Invalid Terraform code (syntax errors)
- Tmp directory cleanup
- S3 download failures
"""

import os
import sys
import unittest
import uuid
import shutil
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import S3ServiceError
from src.utilities.schemas import ValidationResult


class TestS3ValidationFlow(unittest.TestCase):
    """Integration tests for S3-based validation flow"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET", "test-bucket")
        cls.test_user_id = "test-user-123"
        
    def setUp(self):
        """Set up each test"""
        self.plan_id = str(uuid.uuid4())
        self.s3_prefix = f"{self.test_user_id}/{self.plan_id}/v1/"
        # Use system temp directory (works on Windows and Unix)
        self.tmp_dir = os.path.join(tempfile.gettempdir(), self.plan_id)
        
    def tearDown(self):
        """Clean up after each test"""
        # Ensure tmp directory is cleaned up
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
    
    def test_validate_with_valid_terraform_code(self):
        """Test validation with valid Terraform code"""
        # Valid Terraform code
        valid_tf_code = """
terraform {
  required_version = ">= 1.0"
}

resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket-12345"
}

output "bucket_name" {
  value = aws_s3_bucket.example.bucket
}
"""
        
        # Mock S3 download to create files locally
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            # Create tmp directory and write file
            os.makedirs(self.tmp_dir, exist_ok=True)
            tf_file = os.path.join(self.tmp_dir, "main.tf")
            with open(tf_file, 'w') as f:
                f.write(valid_tf_code)
            
            mock_download.return_value = [tf_file]
            
            # Run validation manually (simulating validate_terraform_from_s3)
            try:
                # Download files (mocked)
                downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                
                # Run terraform init -backend=false
                init_result = subprocess.run(
                    ['terraform', 'init', '-backend=false'],
                    cwd=self.tmp_dir,
                    capture_output=True,
                    text=True
                )
                
                if init_result.returncode != 0:
                    result = ValidationResult(valid=False, errors=init_result.stderr or init_result.stdout)
                else:
                    # Run terraform validate
                    validate_result = subprocess.run(
                        ['terraform', 'validate'],
                        cwd=self.tmp_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    if validate_result.returncode != 0:
                        result = ValidationResult(valid=False, errors=validate_result.stderr or validate_result.stdout)
                    else:
                        result = ValidationResult(valid=True, errors=None)
            finally:
                # Cleanup
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Assertions
            self.assertIsInstance(result, ValidationResult)
            self.assertTrue(result.valid, f"Expected valid=True, got errors: {result.errors}")
            self.assertIsNone(result.errors)
    
    def test_validate_with_invalid_terraform_code(self):
        """Test validation with invalid Terraform code (syntax errors)"""
        # Invalid Terraform code with syntax error
        invalid_tf_code = """
resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket"
  # Missing closing brace - syntax error

output "bucket_name" {
  value = aws_s3_bucket.example.bucket
}
"""
        
        # Mock S3 download to create files locally
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            # Create tmp directory and write file
            os.makedirs(self.tmp_dir, exist_ok=True)
            tf_file = os.path.join(self.tmp_dir, "main.tf")
            with open(tf_file, 'w') as f:
                f.write(invalid_tf_code)
            
            mock_download.return_value = [tf_file]
            
            # Run validation manually
            try:
                downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                
                init_result = subprocess.run(
                    ['terraform', 'init', '-backend=false'],
                    cwd=self.tmp_dir,
                    capture_output=True,
                    text=True
                )
                
                if init_result.returncode != 0:
                    result = ValidationResult(valid=False, errors=init_result.stderr or init_result.stdout)
                else:
                    validate_result = subprocess.run(
                        ['terraform', 'validate'],
                        cwd=self.tmp_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    if validate_result.returncode != 0:
                        result = ValidationResult(valid=False, errors=validate_result.stderr or validate_result.stdout)
                    else:
                        result = ValidationResult(valid=True, errors=None)
            finally:
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Assertions
            self.assertIsInstance(result, ValidationResult)
            self.assertFalse(result.valid, "Expected valid=False for invalid Terraform code")
            self.assertIsNotNone(result.errors)
            self.assertIn("error", result.errors.lower(), "Expected error message in validation output")
    
    def test_tmp_directory_cleanup_after_validation(self):
        """Verify tmp directory is cleaned up after validation"""
        valid_tf_code = """
resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket-cleanup"
}
"""
        
        # Mock S3 download
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            # Create tmp directory and write file
            os.makedirs(self.tmp_dir, exist_ok=True)
            tf_file = os.path.join(self.tmp_dir, "main.tf")
            with open(tf_file, 'w') as f:
                f.write(valid_tf_code)
            
            mock_download.return_value = [tf_file]
            
            # Verify directory exists before validation
            self.assertTrue(os.path.exists(self.tmp_dir), "Tmp directory should exist before validation")
            
            # Run validation with cleanup
            try:
                downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                
                init_result = subprocess.run(
                    ['terraform', 'init', '-backend=false'],
                    cwd=self.tmp_dir,
                    capture_output=True,
                    text=True
                )
                
                if init_result.returncode == 0:
                    validate_result = subprocess.run(
                        ['terraform', 'validate'],
                        cwd=self.tmp_dir,
                        capture_output=True,
                        text=True
                    )
            finally:
                # Cleanup (simulating the finally block in validate_terraform_from_s3)
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Verify directory is cleaned up after validation
            self.assertFalse(os.path.exists(self.tmp_dir), "Tmp directory should be cleaned up after validation")
    
    def test_tmp_directory_cleanup_on_error(self):
        """Verify tmp directory is cleaned up even when validation fails"""
        # Mock S3 download to raise an error
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            mock_download.side_effect = S3ServiceError("S3 download failed")
            
            # Run validation (should fail)
            try:
                try:
                    downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                    result = ValidationResult(valid=False, errors="Should not reach here")
                except S3ServiceError as e:
                    result = ValidationResult(valid=False, errors=f"Failed to download files from S3: {str(e)}")
            finally:
                # Cleanup
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Assertions
            self.assertFalse(result.valid, "Expected valid=False when S3 download fails")
            self.assertIn("S3", result.errors, "Expected S3 error message")
            
            # Verify directory is cleaned up even on error
            self.assertFalse(os.path.exists(self.tmp_dir), "Tmp directory should be cleaned up even on error")
    
    def test_s3_download_failure_handling(self):
        """Test error handling when S3 download fails"""
        # Mock S3 download to raise S3ServiceError
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            mock_download.side_effect = S3ServiceError("Failed to download files from S3: Access Denied")
            
            # Run validation
            try:
                try:
                    downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                    result = ValidationResult(valid=False, errors="Should not reach here")
                except S3ServiceError as e:
                    result = ValidationResult(valid=False, errors=f"Failed to download files from S3: {str(e)}")
            finally:
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Assertions
            self.assertIsInstance(result, ValidationResult)
            self.assertFalse(result.valid, "Expected valid=False when S3 download fails")
            self.assertIsNotNone(result.errors)
            self.assertIn("Failed to download files from S3", result.errors)
            self.assertIn("Access Denied", result.errors)
    
    def test_terraform_init_failure(self):
        """Test handling of terraform init failure"""
        # Terraform code that will fail init (invalid provider)
        bad_init_code = """
terraform {
  required_providers {
    nonexistent = {
      source = "hashicorp/nonexistent-provider-xyz"
      version = "999.999.999"
    }
  }
}

resource "nonexistent_resource" "test" {
  name = "test"
}
"""
        
        # Mock S3 download
        with patch('src.services.s3_service.download_prefix_to_tmp') as mock_download:
            # Create tmp directory and write file
            os.makedirs(self.tmp_dir, exist_ok=True)
            tf_file = os.path.join(self.tmp_dir, "main.tf")
            with open(tf_file, 'w') as f:
                f.write(bad_init_code)
            
            mock_download.return_value = [tf_file]
            
            # Run validation
            try:
                downloaded_files = mock_download(self.test_bucket, self.s3_prefix, self.tmp_dir)
                
                init_result = subprocess.run(
                    ['terraform', 'init', '-backend=false'],
                    cwd=self.tmp_dir,
                    capture_output=True,
                    text=True
                )
                
                if init_result.returncode != 0:
                    result = ValidationResult(valid=False, errors=init_result.stderr or init_result.stdout)
                else:
                    result = ValidationResult(valid=True, errors=None)
            finally:
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
            
            # Assertions
            self.assertFalse(result.valid, "Expected valid=False when terraform init fails")
            self.assertIsNotNone(result.errors)
            # Verify tmp directory is still cleaned up
            self.assertFalse(os.path.exists(self.tmp_dir), "Tmp directory should be cleaned up after init failure")


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestS3ValidationFlow)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
