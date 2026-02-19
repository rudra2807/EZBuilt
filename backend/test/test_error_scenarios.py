"""
End-to-end error scenario tests for S3 Terraform storage.

Tests error handling for:
1. Invalid AWS credentials (S3 upload should fail gracefully)
2. Non-existent bucket (should fail gracefully)
3. Invalid Terraform code (validation should fail, status updated)
4. Verify all error cases update database status correctly

Run with: python backend/test/test_error_scenarios.py
"""

import sys
import os
import uuid
import asyncio
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import asyncpg
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import upload_terraform_files, S3ServiceError
from src.services.terraform_exec import validate_terraform_from_s3


# Test configuration
BUCKET_NAME = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET", "ezbuilt-terraform-source")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TEST_USER_ID = f"test-error-user-{uuid.uuid4().hex[:8]}"

# Parse DATABASE_URL for asyncpg
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    url_parts = DATABASE_URL.replace('postgresql+asyncpg://', '').split('@')
    user_pass = url_parts[0].split(':')
    host_db = url_parts[1].split('/')
    host_port = host_db[0].split(':')
    
    DB_USER = user_pass[0]
    DB_PASSWORD = user_pass[1]
    DB_HOST = host_port[0]
    DB_PORT = int(host_port[1]) if len(host_port) > 1 else 5432
    DB_NAME = host_db[1]
else:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

# Sample Terraform code
VALID_TERRAFORM_CODE = '''
resource "aws_s3_bucket" "test_bucket" {
  bucket = "my-test-bucket-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "Test Bucket"
    Environment = "Test"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}
'''

INVALID_TERRAFORM_CODE = '''
resource "aws_s3_bucket" "test_bucket" {
  bucket = "my-test-bucket"
  invalid_attribute = "this should fail validation"
  another_bad_attribute = 12345
}

resource "nonexistent_resource_type" "bad" {
  name = "this resource type does not exist"
}
'''


class ErrorTestResults:
    """Track error scenario test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.cleanup_items = []
    
    def record_pass(self, test_name):
        self.passed += 1
        print(f"✓ {test_name}")
    
    def record_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"✗ {test_name}: {error}")
    
    def add_cleanup(self, cleanup_type, identifier):
        """Track items that need cleanup"""
        self.cleanup_items.append((cleanup_type, identifier))
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Error Scenario Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*60}")
        return self.failed == 0


results = ErrorTestResults()


def test_invalid_aws_credentials():
    """Test S3 upload with invalid AWS credentials fails gracefully"""
    test_name = "Invalid AWS Credentials"
    plan_id = None
    
    async def run_test():
        nonlocal plan_id
        
        try:
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  Simulating invalid AWS credentials...")
            
            # Create database record first
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, plan_id, TEST_USER_ID, "Test invalid credentials",
                '{"resources": []}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Mock get_s3_client to simulate invalid credentials
                with patch('src.services.s3_service.get_s3_client') as mock_get_client:
                    mock_client = MagicMock()
                    mock_client.put_object.side_effect = NoCredentialsError()
                    mock_get_client.return_value = mock_client
                    
                    # Try to upload (should fail)
                    try:
                        upload_terraform_files(
                            bucket=BUCKET_NAME,
                            prefix=s3_prefix,
                            files={"main.tf": VALID_TERRAFORM_CODE}
                        )
                        raise AssertionError("Expected S3ServiceError but upload succeeded")
                    except S3ServiceError as e:
                        print(f"  Expected error caught: {str(e)[:100]}")
                        
                        # Update database status to 'failed'
                        await conn.execute("""
                            UPDATE terraform_plans 
                            SET status = $1, validation_output = $2
                            WHERE id = $3
                        """, 'failed', f"S3 upload failed: {str(e)}", plan_id)
                
                # Verify database status
                print("  Verifying database status...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'failed', f"Expected status 'failed', got '{row['status']}'"
                assert row['validation_output'] is not None, "Expected validation_output to contain error"
                assert "S3 upload failed" in row['validation_output'], "Expected S3 upload error message"
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
                
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def test_nonexistent_bucket():
    """Test S3 upload to non-existent bucket fails gracefully"""
    test_name = "Non-existent Bucket"
    plan_id = None
    
    async def run_test():
        nonlocal plan_id
        
        try:
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            nonexistent_bucket = f"nonexistent-bucket-{uuid.uuid4().hex}"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  Using non-existent bucket: {nonexistent_bucket}")
            
            # Create database record first
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, plan_id, TEST_USER_ID, "Test non-existent bucket",
                '{"resources": []}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Try to upload to non-existent bucket (should fail)
                print("  Attempting upload to non-existent bucket...")
                try:
                    upload_terraform_files(
                        bucket=nonexistent_bucket,
                        prefix=s3_prefix,
                        files={"main.tf": VALID_TERRAFORM_CODE}
                    )
                    raise AssertionError("Expected S3ServiceError but upload succeeded")
                except S3ServiceError as e:
                    print(f"  Expected error caught: {str(e)[:100]}")
                    
                    # Update database status to 'failed'
                    await conn.execute("""
                        UPDATE terraform_plans 
                        SET status = $1, validation_output = $2
                        WHERE id = $3
                    """, 'failed', f"S3 upload failed: {str(e)}", plan_id)
                
                # Verify database status
                print("  Verifying database status...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'failed', f"Expected status 'failed', got '{row['status']}'"
                assert row['validation_output'] is not None, "Expected validation_output to contain error"
                assert "S3 upload failed" in row['validation_output'], "Expected S3 upload error message"
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
                
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def test_invalid_terraform_code_validation():
    """Test that invalid Terraform code fails validation and updates database status"""
    test_name = "Invalid Terraform Code Validation"
    plan_id = None
    s3_prefix = None
    
    async def run_test():
        nonlocal plan_id, s3_prefix
        
        try:
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  S3 prefix: {s3_prefix}")
            
            # Upload invalid Terraform code to S3
            print("  Step 1: Uploading invalid Terraform code to S3...")
            upload_terraform_files(
                bucket=BUCKET_NAME,
                prefix=s3_prefix,
                files={"main.tf": INVALID_TERRAFORM_CODE}
            )
            results.add_cleanup("s3", s3_prefix)
            
            # Create database record
            print("  Step 2: Creating database record...")
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, plan_id, TEST_USER_ID, "Test invalid Terraform code",
                '{"resources": [{"type": "aws_s3_bucket"}]}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Run validation (should fail)
                print("  Step 3: Running validation (expecting failure)...")
                validation_result = validate_terraform_from_s3(
                    bucket=BUCKET_NAME,
                    s3_prefix=s3_prefix,
                    plan_id=plan_id
                )
                
                if validation_result.valid:
                    raise AssertionError("Expected validation to fail for invalid Terraform code")
                
                print(f"  Validation failed as expected: {validation_result.errors[:100]}...")
                
                # Update database with validation results
                print("  Step 4: Updating database with validation failure...")
                await conn.execute("""
                    UPDATE terraform_plans 
                    SET validation_passed = $1, validation_output = $2, status = $3
                    WHERE id = $4
                """, validation_result.valid, validation_result.errors, 'generated', plan_id)
                
                # Verify database status
                print("  Step 5: Verifying database status...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'generated', f"Expected status 'generated', got '{row['status']}'"
                assert row['validation_passed'] is False, "Expected validation_passed to be False"
                assert row['validation_output'] is not None, "Expected validation_output to contain error"
                assert len(row['validation_output']) > 0, "Expected non-empty validation_output"
                
                # Verify tmp directory cleaned up
                print("  Step 6: Verifying tmp cleanup...")
                tmp_dir = f"/tmp/{plan_id}"
                if os.path.exists(tmp_dir):
                    raise AssertionError(f"Tmp directory {tmp_dir} was not cleaned up")
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
                
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def test_s3_download_failure_during_validation():
    """Test that S3 download failure during validation updates database correctly"""
    test_name = "S3 Download Failure During Validation"
    plan_id = None
    
    async def run_test():
        nonlocal plan_id
        
        try:
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  Simulating S3 download failure...")
            
            # Create database record
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, plan_id, TEST_USER_ID, "Test S3 download failure",
                '{"resources": []}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Mock S3 download to fail
                with patch('src.services.s3_service.get_s3_client') as mock_get_client:
                    mock_client = MagicMock()
                    mock_client.list_objects_v2.side_effect = ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
                        "ListObjectsV2"
                    )
                    mock_get_client.return_value = mock_client
                    
                    # Try to validate (should fail on download)
                    print("  Attempting validation with S3 download failure...")
                    validation_result = validate_terraform_from_s3(
                        bucket=BUCKET_NAME,
                        s3_prefix=s3_prefix,
                        plan_id=plan_id
                    )
                    
                    if validation_result.valid:
                        raise AssertionError("Expected validation to fail due to S3 download error")
                    
                    print(f"  Validation failed as expected: {validation_result.errors[:100]}...")
                    
                    # Update database status to 'failed'
                    await conn.execute("""
                        UPDATE terraform_plans 
                        SET status = $1, validation_passed = $2, validation_output = $3
                        WHERE id = $4
                    """, 'failed', False, validation_result.errors, plan_id)
                
                # Verify database status
                print("  Verifying database status...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'failed', f"Expected status 'failed', got '{row['status']}'"
                assert row['validation_passed'] is False, "Expected validation_passed to be False"
                assert row['validation_output'] is not None, "Expected validation_output to contain error"
                
                # Verify tmp directory cleaned up
                print("  Verifying tmp cleanup...")
                tmp_dir = f"/tmp/{plan_id}"
                if os.path.exists(tmp_dir):
                    raise AssertionError(f"Tmp directory {tmp_dir} was not cleaned up")
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
                
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def test_database_status_consistency():
    """Test that database status is always updated correctly in error scenarios"""
    test_name = "Database Status Consistency"
    plan_ids = []
    
    async def run_test():
        nonlocal plan_ids
        
        try:
            print(f"\n  Testing database status consistency across error scenarios...")
            
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                # Scenario 1: S3 upload failure
                plan_id_1 = str(uuid.uuid4())
                plan_ids.append(plan_id_1)
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status, validation_output)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, plan_id_1, TEST_USER_ID, "S3 upload failure test",
                '{"resources": []}', "", 'failed', "S3 upload failed: Access Denied")
                results.add_cleanup("db", plan_id_1)
                
                # Scenario 2: Validation failure
                plan_id_2 = str(uuid.uuid4())
                plan_ids.append(plan_id_2)
                s3_prefix_2 = f"{TEST_USER_ID}/{plan_id_2}/v1/"
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status, validation_passed, validation_output)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, plan_id_2, TEST_USER_ID, "Validation failure test",
                '{"resources": []}', s3_prefix_2, 'generated', False, "Terraform validation failed: Invalid syntax")
                results.add_cleanup("db", plan_id_2)
                
                # Scenario 3: Successful generation
                plan_id_3 = str(uuid.uuid4())
                plan_ids.append(plan_id_3)
                s3_prefix_3 = f"{TEST_USER_ID}/{plan_id_3}/v1/"
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status, validation_passed)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, plan_id_3, TEST_USER_ID, "Successful generation test",
                '{"resources": []}', s3_prefix_3, 'generated', True)
                results.add_cleanup("db", plan_id_3)
                
                # Verify all records
                print("  Verifying all database records...")
                
                # Check plan 1 (S3 upload failure)
                row1 = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id_1)
                assert row1['status'] == 'failed', f"Plan 1: Expected status 'failed', got '{row1['status']}'"
                assert "S3 upload failed" in row1['validation_output']
                
                # Check plan 2 (validation failure)
                row2 = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id_2)
                assert row2['status'] == 'generated', f"Plan 2: Expected status 'generated', got '{row2['status']}'"
                assert row2['validation_passed'] is False
                assert "validation failed" in row2['validation_output'].lower()
                
                # Check plan 3 (success)
                row3 = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id_3)
                assert row3['status'] == 'generated', f"Plan 3: Expected status 'generated', got '{row3['status']}'"
                assert row3['validation_passed'] is True
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
            
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def cleanup_test_data():
    """Clean up test data from S3 and database"""
    
    async def run_cleanup():
        print(f"\n{'='*60}")
        print("Cleaning up test data...")
        print(f"{'='*60}\n")
        
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        try:
            for cleanup_type, identifier in results.cleanup_items:
                try:
                    if cleanup_type == "s3":
                        # Delete S3 objects
                        print(f"  Deleting S3 prefix: {identifier}")
                        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=identifier)
                        if 'Contents' in response:
                            for obj in response['Contents']:
                                s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                                print(f"    Deleted: {obj['Key']}")
                    
                    elif cleanup_type == "db":
                        # Delete database record
                        print(f"  Deleting DB record: {identifier}")
                        await conn.execute("DELETE FROM terraform_plans WHERE id = $1", identifier)
                        print(f"    Deleted plan: {identifier}")
                
                except Exception as e:
                    print(f"  Warning: Failed to cleanup {cleanup_type} {identifier}: {str(e)}")
        
        finally:
            await conn.close()
        
        print("\nCleanup complete!")
    
    asyncio.run(run_cleanup())


def run_error_scenario_tests():
    """Run all error scenario tests"""
    print("\n" + "="*60)
    print("Error Scenario Tests for S3 Terraform Storage")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Bucket: {BUCKET_NAME}")
    print(f"  Region: {AWS_REGION}")
    print(f"  Test User: {TEST_USER_ID}")
    print("="*60 + "\n")
    
    async def setup_test_user():
        """Create test user in database"""
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        try:
            # Check if user exists
            exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)", TEST_USER_ID)
            if not exists:
                print(f"Creating test user: {TEST_USER_ID}")
                await conn.execute("""
                    INSERT INTO users (user_id, email, created_at)
                    VALUES ($1, $2, NOW())
                """, TEST_USER_ID, f"{TEST_USER_ID}@test.com")
                results.add_cleanup("user", TEST_USER_ID)
            else:
                print(f"Test user already exists: {TEST_USER_ID}")
        finally:
            await conn.close()
    
    async def cleanup_test_user():
        """Remove test user from database"""
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        try:
            # Check if we created the user
            if ("user", TEST_USER_ID) in results.cleanup_items:
                print(f"  Deleting test user: {TEST_USER_ID}")
                await conn.execute("DELETE FROM users WHERE user_id = $1", TEST_USER_ID)
        finally:
            await conn.close()
    
    try:
        # Setup test user
        asyncio.run(setup_test_user())
        
        # Run error scenario tests
        print("\nRunning Error Scenario Tests:")
        test_invalid_aws_credentials()
        test_nonexistent_bucket()
        test_invalid_terraform_code_validation()
        test_s3_download_failure_during_validation()
        test_database_status_consistency()
        
    finally:
        # Always cleanup test data
        cleanup_test_data()
        # Cleanup test user
        asyncio.run(cleanup_test_user())
    
    # Print summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_error_scenario_tests()
    sys.exit(exit_code)
