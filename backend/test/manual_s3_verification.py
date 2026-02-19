#!/usr/bin/env python3
"""
Manual verification script for S3 service and validation functions.

This script tests the core services independently:
1. S3 upload/download functions with a test bucket
2. Validation function with local files

Run this script to verify the implementation works with real AWS resources.
"""

import os
import sys
import uuid
import shutil
import tempfile

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import upload_terraform_files, download_prefix_to_tmp, S3ServiceError
from src.services.terraform_exec import validate_terraform_from_s3
from src.utilities.schemas import ValidationResult


def test_s3_upload_download():
    """Test S3 upload and download functions with a test bucket"""
    print("\n" + "="*70)
    print("TEST 1: S3 Upload/Download Functions")
    print("="*70)
    
    # Get bucket from environment
    bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET")
    if not bucket:
        print("❌ SKIPPED: EZBUILT_TERRAFORM_SOURCE_BUCKET not set in environment")
        print("   Set this variable to test with a real S3 bucket")
        return False
    
    print(f"✓ Using bucket: {bucket}")
    
    # Generate test data
    test_user_id = "test-user-manual"
    test_plan_id = str(uuid.uuid4())
    s3_prefix = f"{test_user_id}/{test_plan_id}/v1/"
    
    test_files = {
        "main.tf": """
terraform {
  required_version = ">= 1.0"
}

resource "aws_s3_bucket" "test" {
  bucket = "my-test-bucket-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

output "bucket_name" {
  value = aws_s3_bucket.test.bucket
}
""",
        "variables.tf": """
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
"""
    }
    
    print(f"✓ Test prefix: {s3_prefix}")
    print(f"✓ Files to upload: {list(test_files.keys())}")
    
    # Test upload
    print("\n--- Testing Upload ---")
    try:
        upload_terraform_files(bucket, s3_prefix, test_files)
        print("✅ Upload successful")
    except S3ServiceError as e:
        print(f"❌ Upload failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during upload: {e}")
        return False
    
    # Test download
    print("\n--- Testing Download ---")
    tmp_dir = os.path.join(tempfile.gettempdir(), f"s3_test_{test_plan_id}")
    
    try:
        downloaded_files = download_prefix_to_tmp(bucket, s3_prefix, tmp_dir)
        print(f"✅ Download successful: {len(downloaded_files)} files")
        
        # Verify files exist locally
        for file_path in downloaded_files:
            if os.path.exists(file_path):
                print(f"   ✓ {os.path.basename(file_path)} exists")
            else:
                print(f"   ❌ {os.path.basename(file_path)} missing")
                return False
        
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            print("✓ Cleaned up tmp directory")
        
        print("\n✅ TEST 1 PASSED: S3 upload/download works correctly")
        return True
        
    except S3ServiceError as e:
        print(f"❌ Download failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during download: {e}")
        return False
    finally:
        # Ensure cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def test_validation_with_local_files():
    """Test validation function with local files (no S3)"""
    print("\n" + "="*70)
    print("TEST 2: Validation Function with Local Files")
    print("="*70)
    
    # Create temporary directory with valid Terraform code
    test_plan_id = str(uuid.uuid4())
    tmp_dir = os.path.join(tempfile.gettempdir(), f"validation_test_{test_plan_id}")
    
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        print(f"✓ Created test directory: {tmp_dir}")
        
        # Write valid Terraform code
        valid_tf_code = """
terraform {
  required_version = ">= 1.0"
}

resource "aws_s3_bucket" "example" {
  bucket = "my-validation-test-bucket"
}

output "bucket_id" {
  value = aws_s3_bucket.example.id
}
"""
        
        tf_file = os.path.join(tmp_dir, "main.tf")
        with open(tf_file, 'w') as f:
            f.write(valid_tf_code)
        print("✓ Created main.tf with valid Terraform code")
        
        # Run terraform init
        print("\n--- Running terraform init ---")
        import subprocess
        init_result = subprocess.run(
            ['terraform', 'init', '-backend=false'],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )
        
        if init_result.returncode != 0:
            print(f"❌ Terraform init failed:")
            print(init_result.stderr or init_result.stdout)
            return False
        print("✅ Terraform init successful")
        
        # Run terraform validate
        print("\n--- Running terraform validate ---")
        validate_result = subprocess.run(
            ['terraform', 'validate'],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )
        
        if validate_result.returncode != 0:
            print(f"❌ Terraform validate failed:")
            print(validate_result.stderr or validate_result.stdout)
            return False
        print("✅ Terraform validate successful")
        
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
            print("✓ Cleaned up tmp directory")
        
        print("\n✅ TEST 2 PASSED: Validation works with local files")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Ensure cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def test_full_s3_validation_flow():
    """Test the complete validate_terraform_from_s3 function"""
    print("\n" + "="*70)
    print("TEST 3: Full S3 Validation Flow (validate_terraform_from_s3)")
    print("="*70)
    
    # Get bucket from environment
    bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET")
    if not bucket:
        print("❌ SKIPPED: EZBUILT_TERRAFORM_SOURCE_BUCKET not set in environment")
        return False
    
    print(f"✓ Using bucket: {bucket}")
    
    # Generate test data
    test_user_id = "test-user-validation"
    test_plan_id = str(uuid.uuid4())
    s3_prefix = f"{test_user_id}/{test_plan_id}/v1/"
    
    test_files = {
        "main.tf": """
terraform {
  required_version = ">= 1.0"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "test-vpc"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}
"""
    }
    
    print(f"✓ Test prefix: {s3_prefix}")
    
    # Upload files to S3
    print("\n--- Uploading files to S3 ---")
    try:
        upload_terraform_files(bucket, s3_prefix, test_files)
        print("✅ Upload successful")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False
    
    # Run validation from S3
    print("\n--- Running validate_terraform_from_s3 ---")
    try:
        result = validate_terraform_from_s3(bucket, s3_prefix, test_plan_id)
        
        if result.valid:
            print("✅ Validation successful")
            print(f"   Valid: {result.valid}")
            print(f"   Errors: {result.errors}")
        else:
            print(f"❌ Validation failed:")
            print(f"   Valid: {result.valid}")
            print(f"   Errors: {result.errors}")
            return False
        
        # Verify tmp directory was cleaned up
        tmp_dir = f"/tmp/{test_plan_id}"
        if os.path.exists(tmp_dir):
            print(f"❌ Tmp directory still exists: {tmp_dir}")
            return False
        else:
            print(f"✓ Tmp directory cleaned up: {tmp_dir}")
        
        print("\n✅ TEST 3 PASSED: Full S3 validation flow works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        return False


def main():
    """Run all verification tests"""
    print("\n" + "="*70)
    print("MANUAL S3 SERVICE VERIFICATION")
    print("="*70)
    print("\nThis script verifies that core services work independently:")
    print("1. S3 upload/download functions")
    print("2. Validation function with local files")
    print("3. Full S3 validation flow")
    
    # Check AWS credentials
    print("\n--- Checking AWS Configuration ---")
    aws_region = os.environ.get("AWS_REGION", "not set")
    s3_bucket = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET", "not set")
    
    print(f"AWS_REGION: {aws_region}")
    print(f"EZBUILT_TERRAFORM_SOURCE_BUCKET: {s3_bucket}")
    
    if s3_bucket == "not set":
        print("\n⚠️  WARNING: EZBUILT_TERRAFORM_SOURCE_BUCKET not set")
        print("   Tests requiring S3 will be skipped")
        print("   Set this variable to test with a real S3 bucket")
    
    # Run tests
    results = []
    
    # Test 1: S3 upload/download (requires bucket)
    results.append(("S3 Upload/Download", test_s3_upload_download()))
    
    # Test 2: Local validation (no S3 required)
    results.append(("Local Validation", test_validation_with_local_files()))
    
    # Test 3: Full S3 validation flow (requires bucket)
    results.append(("Full S3 Validation", test_full_s3_validation_flow()))
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED/SKIPPED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nCore services are working correctly:")
        print("✓ S3 upload/download functions work with test bucket")
        print("✓ Validation function works with local files")
        print("✓ Full S3 validation flow works end-to-end")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED OR WERE SKIPPED")
        print("\nPlease review the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
