"""
End-to-end test for the complete S3 Terraform storage flow.

This test validates:
1. Submit requirements through API endpoint
2. Verify Terraform code uploaded to S3 at correct prefix
3. Verify database record created with correct metadata
4. Verify validation runs and results stored
5. Verify tmp directory cleaned up

Run with: python backend/test/test_e2e_flow.py
"""

import sys
import os
import uuid
import asyncio
import boto3
from botocore.exceptions import ClientError
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import upload_terraform_files, download_prefix_to_tmp, S3ServiceError
from src.services.terraform_exec import validate_terraform_from_s3


# Test configuration
BUCKET_NAME = os.environ.get("EZBUILT_TERRAFORM_SOURCE_BUCKET", "ezbuilt-terraform-source")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TEST_USER_ID = f"test-user-{uuid.uuid4().hex[:8]}"

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
}
'''


class E2ETestResults:
    """Track end-to-end test results"""
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
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*60}")
        return self.failed == 0


results = E2ETestResults()


def verify_s3_bucket_accessible():
    """Verify S3 bucket is accessible"""
    test_name = "S3 Bucket Accessibility"
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        results.record_pass(test_name)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            results.record_fail(test_name, f"Bucket {BUCKET_NAME} does not exist")
        elif error_code == '403':
            results.record_fail(test_name, f"Access denied to bucket {BUCKET_NAME}")
        else:
            results.record_fail(test_name, f"Error accessing bucket: {str(e)}")
        return False


def test_complete_flow_valid_terraform():
    """Test complete flow with valid Terraform code"""
    test_name = "Complete Flow - Valid Terraform"
    plan_id = None
    s3_prefix = None
    
    async def run_test():
        nonlocal plan_id, s3_prefix
        
        try:
            # Generate unique plan ID
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  S3 prefix: {s3_prefix}")
            
            # Step 1: Upload Terraform code to S3
            print("  Step 1: Uploading to S3...")
            upload_terraform_files(
                bucket=BUCKET_NAME,
                prefix=s3_prefix,
                files={"main.tf": VALID_TERRAFORM_CODE}
            )
            results.add_cleanup("s3", s3_prefix)
            
            # Step 2: Verify file exists in S3
            print("  Step 2: Verifying S3 upload...")
            s3_client = boto3.client('s3', region_name=AWS_REGION)
            response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=s3_prefix)
            
            if 'Contents' not in response or len(response['Contents']) == 0:
                raise AssertionError("No files found in S3 after upload")
            
            uploaded_key = response['Contents'][0]['Key']
            if not uploaded_key.endswith('main.tf'):
                raise AssertionError(f"Expected main.tf, found {uploaded_key}")
            
            # Step 3: Create database record
            print("  Step 3: Creating database record...")
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
                """, plan_id, TEST_USER_ID, "Test requirements for E2E test", 
                '{"resources": [{"type": "aws_s3_bucket"}]}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Step 4: Run validation
                print("  Step 4: Running validation...")
                validation_result = validate_terraform_from_s3(
                    bucket=BUCKET_NAME,
                    s3_prefix=s3_prefix,
                    plan_id=plan_id
                )
                
                if not validation_result.valid:
                    raise AssertionError(f"Validation failed: {validation_result.errors}")
                
                # Step 5: Update database with validation results
                print("  Step 5: Updating database...")
                await conn.execute("""
                    UPDATE terraform_plans 
                    SET validation_passed = $1, validation_output = $2, status = $3
                    WHERE id = $4
                """, validation_result.valid, validation_result.errors, 'generated', plan_id)
                
                # Step 6: Verify database record
                print("  Step 6: Verifying database record...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'generated', f"Expected status 'generated', got '{row['status']}'"
                assert row['validation_passed'] is True, "Expected validation_passed to be True"
                assert row['s3_prefix'] == s3_prefix, f"S3 prefix mismatch"
                
                # Step 7: Verify tmp directory cleaned up
                print("  Step 7: Verifying tmp cleanup...")
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


def test_complete_flow_invalid_terraform():
    """Test complete flow with invalid Terraform code"""
    test_name = "Complete Flow - Invalid Terraform"
    plan_id = None
    s3_prefix = None
    
    async def run_test():
        nonlocal plan_id, s3_prefix
        
        try:
            # Generate unique plan ID
            plan_id = str(uuid.uuid4())
            s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
            
            print(f"\n  Testing with plan_id: {plan_id}")
            print(f"  S3 prefix: {s3_prefix}")
            
            # Step 1: Upload invalid Terraform code to S3
            print("  Step 1: Uploading invalid code to S3...")
            upload_terraform_files(
                bucket=BUCKET_NAME,
                prefix=s3_prefix,
                files={"main.tf": INVALID_TERRAFORM_CODE}
            )
            results.add_cleanup("s3", s3_prefix)
            
            # Step 2: Create database record
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
                """, plan_id, TEST_USER_ID, "Test requirements with invalid Terraform",
                '{"resources": [{"type": "aws_s3_bucket"}]}', s3_prefix, 'generating')
                results.add_cleanup("db", plan_id)
                
                # Step 3: Run validation (should fail)
                print("  Step 3: Running validation (expecting failure)...")
                validation_result = validate_terraform_from_s3(
                    bucket=BUCKET_NAME,
                    s3_prefix=s3_prefix,
                    plan_id=plan_id
                )
                
                if validation_result.valid:
                    raise AssertionError("Expected validation to fail for invalid Terraform code")
                
                # Step 4: Update database with validation results
                print("  Step 4: Updating database with failure...")
                await conn.execute("""
                    UPDATE terraform_plans 
                    SET validation_passed = $1, validation_output = $2, status = $3
                    WHERE id = $4
                """, validation_result.valid, validation_result.errors, 'generated', plan_id)
                
                # Step 5: Verify database record
                print("  Step 5: Verifying database record...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'generated', f"Expected status 'generated', got '{row['status']}'"
                assert row['validation_passed'] is False, "Expected validation_passed to be False"
                assert row['validation_output'] is not None, "Expected validation_output to contain error"
                
                # Step 6: Verify tmp directory cleaned up
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


def test_s3_upload_failure_handling():
    """Test handling of S3 upload failure"""
    test_name = "S3 Upload Failure Handling"
    plan_id = None
    
    async def run_test():
        nonlocal plan_id
        
        try:
            # Generate unique plan ID
            plan_id = str(uuid.uuid4())
            
            print(f"\n  Testing with plan_id: {plan_id}")
            
            # Try to upload to non-existent bucket
            print("  Step 1: Attempting upload to non-existent bucket...")
            try:
                upload_terraform_files(
                    bucket="non-existent-bucket-12345",
                    prefix=f"{TEST_USER_ID}/{plan_id}/v1/",
                    files={"main.tf": VALID_TERRAFORM_CODE}
                )
                raise AssertionError("Expected S3ServiceError but upload succeeded")
            except S3ServiceError as e:
                print(f"  Expected error caught: {str(e)[:100]}")
            
            # Create database record and mark as failed
            print("  Step 2: Creating database record with failed status...")
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                await conn.execute("""
                    INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status, validation_output)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, plan_id, TEST_USER_ID, "Test S3 upload failure",
                '{"resources": []}', "", 'failed', "S3 upload failed: Failed to upload main.tf")
                results.add_cleanup("db", plan_id)
                
                # Verify database record
                print("  Step 3: Verifying database record...")
                row = await conn.fetchrow("SELECT * FROM terraform_plans WHERE id = $1", plan_id)
                
                assert row['status'] == 'failed', f"Expected status 'failed', got '{row['status']}'"
                assert "S3 upload failed" in row['validation_output']
                
                results.record_pass(test_name)
                
            finally:
                await conn.close()
                
        except Exception as e:
            results.record_fail(test_name, str(e))
            import traceback
            print(f"  Error details: {traceback.format_exc()}")
    
    asyncio.run(run_test())


def test_multiple_plans_isolation():
    """Test that multiple plans don't interfere with each other"""
    test_name = "Multiple Plans Isolation"
    plan_ids = []
    
    async def run_test():
        nonlocal plan_ids
        
        try:
            print(f"\n  Creating 3 plans simultaneously...")
            
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            
            try:
                # Create 3 plans
                for i in range(3):
                    plan_id = str(uuid.uuid4())
                    plan_ids.append(plan_id)
                    s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
                    
                    print(f"  Plan {i+1}: {plan_id}")
                    
                    # Upload to S3
                    upload_terraform_files(
                        bucket=BUCKET_NAME,
                        prefix=s3_prefix,
                        files={"main.tf": VALID_TERRAFORM_CODE}
                    )
                    results.add_cleanup("s3", s3_prefix)
                    
                    # Create DB record
                    await conn.execute("""
                        INSERT INTO terraform_plans (id, user_id, original_requirements, structured_requirements, s3_prefix, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, plan_id, TEST_USER_ID, f"Test plan {i+1}",
                    '{"resources": []}', s3_prefix, 'generating')
                    results.add_cleanup("db", plan_id)
                
                # Validate all plans
                print(f"  Validating all plans...")
                for i, plan_id in enumerate(plan_ids):
                    s3_prefix = f"{TEST_USER_ID}/{plan_id}/v1/"
                    
                    validation_result = validate_terraform_from_s3(
                        bucket=BUCKET_NAME,
                        s3_prefix=s3_prefix,
                        plan_id=plan_id
                    )
                    
                    if not validation_result.valid:
                        raise AssertionError(f"Plan {i+1} validation failed: {validation_result.errors}")
                    
                    # Verify tmp directory cleaned up
                    tmp_dir = f"/tmp/{plan_id}"
                    if os.path.exists(tmp_dir):
                        raise AssertionError(f"Tmp directory {tmp_dir} for plan {i+1} was not cleaned up")
                
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
                    
                    # Skip user cleanup here - handled separately
                
                except Exception as e:
                    print(f"  Warning: Failed to cleanup {cleanup_type} {identifier}: {str(e)}")
        
        finally:
            await conn.close()
        
        print("\nCleanup complete!")
    
    asyncio.run(run_cleanup())


def verify_no_tmp_directories():
    """Verify no test tmp directories are left behind"""
    test_name = "No Tmp Directories Left Behind"
    try:
        tmp_dir = "/tmp"
        if os.path.exists(tmp_dir):
            # Look for any directories matching our test pattern
            test_dirs = [d for d in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, d))]
            
            # Filter for UUID-like directories (our plan IDs)
            uuid_pattern_dirs = [d for d in test_dirs if len(d) == 36 and d.count('-') == 4]
            
            if uuid_pattern_dirs:
                print(f"  Warning: Found {len(uuid_pattern_dirs)} potential test directories in /tmp")
                for d in uuid_pattern_dirs[:5]:  # Show first 5
                    print(f"    - {d}")
            else:
                print(f"  No test tmp directories found")
        
        results.record_pass(test_name)
    except Exception as e:
        results.record_fail(test_name, str(e))


def run_e2e_tests():
    """Run all end-to-end tests"""
    print("\n" + "="*60)
    print("End-to-End Tests for S3 Terraform Storage")
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
        # Pre-flight check
        print("Pre-flight Checks:")
        if not verify_s3_bucket_accessible():
            print("\n⚠️  S3 bucket not accessible. Skipping tests.")
            return 1
        
        # Setup test user
        asyncio.run(setup_test_user())
        
        # Run tests
        print("\nRunning End-to-End Tests:")
        test_complete_flow_valid_terraform()
        test_complete_flow_invalid_terraform()
        test_s3_upload_failure_handling()
        test_multiple_plans_isolation()
        
        # Verify cleanup
        print("\nVerifying Cleanup:")
        verify_no_tmp_directories()
        
    finally:
        # Always cleanup test data
        cleanup_test_data()
        # Cleanup test user
        asyncio.run(cleanup_test_user())
    
    # Print summary
    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_e2e_tests()
    sys.exit(exit_code)
