#!/usr/bin/env python3
"""
Unit tests for S3 service functions.

Tests the s3_service.py module with mocked boto3 client:
- upload_terraform_files with valid inputs
- download_prefix_to_tmp with valid prefix
- Error handling for ClientError exceptions
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_service import (
    S3ServiceError,
    get_s3_client,
    upload_terraform_files,
    download_prefix_to_tmp
)


class TestS3ServiceGetClient(unittest.TestCase):
    """Test get_s3_client function"""
    
    @patch('src.services.s3_service.boto3.client')
    def test_get_s3_client_default_region(self, mock_boto_client):
        """Test S3 client creation with default region"""
        # Remove AWS_REGION if set
        with patch.dict(os.environ, {}, clear=False):
            if 'AWS_REGION' in os.environ:
                del os.environ['AWS_REGION']
            
            get_s3_client()
            
            # Verify boto3.client was called with default region
            mock_boto_client.assert_called_once_with('s3', region_name='us-east-1')
    
    @patch('src.services.s3_service.boto3.client')
    def test_get_s3_client_custom_region(self, mock_boto_client):
        """Test S3 client creation with custom region from environment"""
        with patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}):
            get_s3_client()
            
            # Verify boto3.client was called with custom region
            mock_boto_client.assert_called_once_with('s3', region_name='eu-west-1')


class TestS3ServiceUpload(unittest.TestCase):
    """Test upload_terraform_files function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_bucket = "test-bucket"
        self.test_prefix = "user123/plan456/v1/"
        self.test_files = {
            "main.tf": "resource \"aws_s3_bucket\" \"example\" {\n  bucket = \"test\"\n}",
            "variables.tf": "variable \"region\" {\n  default = \"us-east-1\"\n}"
        }
    
    @patch('src.services.s3_service.get_s3_client')
    def test_upload_single_file_success(self, mock_get_client):
        """Test successful upload of a single file"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Upload single file
        files = {"main.tf": "resource \"aws_s3_bucket\" \"test\" {}"}
        upload_terraform_files(self.test_bucket, self.test_prefix, files)
        
        # Verify put_object was called correctly
        mock_client.put_object.assert_called_once_with(
            Bucket=self.test_bucket,
            Key=f"{self.test_prefix}main.tf",
            Body=files["main.tf"].encode('utf-8'),
            ContentType='text/plain',
            ServerSideEncryption='AES256'
        )
    
    @patch('src.services.s3_service.get_s3_client')
    def test_upload_multiple_files_success(self, mock_get_client):
        """Test successful upload of multiple files"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Upload multiple files
        upload_terraform_files(self.test_bucket, self.test_prefix, self.test_files)
        
        # Verify put_object was called for each file
        self.assertEqual(mock_client.put_object.call_count, 2)
        
        # Verify calls were made with correct parameters
        expected_calls = [
            call(
                Bucket=self.test_bucket,
                Key=f"{self.test_prefix}main.tf",
                Body=self.test_files["main.tf"].encode('utf-8'),
                ContentType='text/plain',
                ServerSideEncryption='AES256'
            ),
            call(
                Bucket=self.test_bucket,
                Key=f"{self.test_prefix}variables.tf",
                Body=self.test_files["variables.tf"].encode('utf-8'),
                ContentType='text/plain',
                ServerSideEncryption='AES256'
            )
        ]
        mock_client.put_object.assert_has_calls(expected_calls, any_order=True)
    
    @patch('src.services.s3_service.get_s3_client')
    def test_upload_with_client_error(self, mock_get_client):
        """Test upload failure with ClientError"""
        # Mock S3 client to raise ClientError
        mock_client = MagicMock()
        mock_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'PutObject'
        )
        mock_get_client.return_value = mock_client
        
        # Attempt upload and expect S3ServiceError
        files = {"main.tf": "resource \"aws_s3_bucket\" \"test\" {}"}
        with self.assertRaises(S3ServiceError) as context:
            upload_terraform_files(self.test_bucket, self.test_prefix, files)
        
        # Verify error message contains relevant information
        self.assertIn("Failed to upload main.tf", str(context.exception))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_upload_empty_files_dict(self, mock_get_client):
        """Test upload with empty files dictionary"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Upload empty dict (should not raise error, just do nothing)
        upload_terraform_files(self.test_bucket, self.test_prefix, {})
        
        # Verify put_object was never called
        mock_client.put_object.assert_not_called()
    
    @patch('src.services.s3_service.get_s3_client')
    def test_upload_with_special_characters(self, mock_get_client):
        """Test upload with special characters in content"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Upload file with special characters
        files = {"main.tf": "# Comment with special chars: @#$%^&*()\nresource \"aws_s3_bucket\" \"test\" {}"}
        upload_terraform_files(self.test_bucket, self.test_prefix, files)
        
        # Verify put_object was called with encoded content
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args
        self.assertEqual(call_args[1]['Body'], files["main.tf"].encode('utf-8'))


class TestS3ServiceDownload(unittest.TestCase):
    """Test download_prefix_to_tmp function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_bucket = "test-bucket"
        self.test_prefix = "user123/plan456/v1/"
        # Use system temp directory
        self.test_local_path = os.path.join(tempfile.gettempdir(), "test_s3_download")
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_local_path):
            shutil.rmtree(self.test_local_path)
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_single_file_success(self, mock_get_client):
        """Test successful download of a single file"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f"{self.test_prefix}main.tf"}
            ]
        }
        mock_get_client.return_value = mock_client
        
        # Download files
        result = download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify list_objects_v2 was called
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket=self.test_bucket,
            Prefix=self.test_prefix
        )
        
        # Verify download_file was called
        mock_client.download_file.assert_called_once_with(
            self.test_bucket,
            f"{self.test_prefix}main.tf",
            os.path.join(self.test_local_path, "main.tf")
        )
        
        # Verify return value
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], os.path.join(self.test_local_path, "main.tf"))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_multiple_files_success(self, mock_get_client):
        """Test successful download of multiple files"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f"{self.test_prefix}main.tf"},
                {'Key': f"{self.test_prefix}variables.tf"},
                {'Key': f"{self.test_prefix}outputs.tf"}
            ]
        }
        mock_get_client.return_value = mock_client
        
        # Download files
        result = download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify download_file was called for each file
        self.assertEqual(mock_client.download_file.call_count, 3)
        
        # Verify return value contains all files
        self.assertEqual(len(result), 3)
        self.assertIn(os.path.join(self.test_local_path, "main.tf"), result)
        self.assertIn(os.path.join(self.test_local_path, "variables.tf"), result)
        self.assertIn(os.path.join(self.test_local_path, "outputs.tf"), result)
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_with_subdirectories(self, mock_get_client):
        """Test download with files in subdirectories"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f"{self.test_prefix}main.tf"},
                {'Key': f"{self.test_prefix}modules/vpc/main.tf"},
                {'Key': f"{self.test_prefix}modules/vpc/variables.tf"}
            ]
        }
        mock_get_client.return_value = mock_client
        
        # Download files
        result = download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify download_file was called for each file
        self.assertEqual(mock_client.download_file.call_count, 3)
        
        # Verify return value contains all files (normalize paths for cross-platform compatibility)
        self.assertEqual(len(result), 3)
        result_normalized = [os.path.normpath(p) for p in result]
        self.assertIn(os.path.normpath(os.path.join(self.test_local_path, "main.tf")), result_normalized)
        self.assertIn(os.path.normpath(os.path.join(self.test_local_path, "modules", "vpc", "main.tf")), result_normalized)
        self.assertIn(os.path.normpath(os.path.join(self.test_local_path, "modules", "vpc", "variables.tf")), result_normalized)
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_no_files_found(self, mock_get_client):
        """Test download when no files exist under prefix"""
        # Mock S3 client with empty response
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}  # No 'Contents' key
        mock_get_client.return_value = mock_client
        
        # Attempt download and expect S3ServiceError
        with self.assertRaises(S3ServiceError) as context:
            download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify error message
        self.assertIn("No files found under prefix", str(context.exception))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_with_list_objects_error(self, mock_get_client):
        """Test download failure when listing objects fails"""
        # Mock S3 client to raise ClientError on list_objects_v2
        mock_client = MagicMock()
        mock_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}},
            'ListObjectsV2'
        )
        mock_get_client.return_value = mock_client
        
        # Attempt download and expect S3ServiceError
        with self.assertRaises(S3ServiceError) as context:
            download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify error message contains relevant information
        self.assertIn("Failed to download files", str(context.exception))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_with_download_file_error(self, mock_get_client):
        """Test download failure when downloading individual file fails"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f"{self.test_prefix}main.tf"}
            ]
        }
        # Make download_file raise ClientError
        mock_client.download_file.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GetObject'
        )
        mock_get_client.return_value = mock_client
        
        # Attempt download and expect S3ServiceError
        with self.assertRaises(S3ServiceError) as context:
            download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify error message
        self.assertIn("Failed to download files", str(context.exception))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_creates_local_directory(self, mock_get_client):
        """Test that download creates local directory if it doesn't exist"""
        # Mock S3 client
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': f"{self.test_prefix}main.tf"}
            ]
        }
        mock_get_client.return_value = mock_client
        
        # Ensure directory doesn't exist
        if os.path.exists(self.test_local_path):
            shutil.rmtree(self.test_local_path)
        
        # Download files
        download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify directory was created
        self.assertTrue(os.path.exists(self.test_local_path))
    
    @patch('src.services.s3_service.get_s3_client')
    def test_download_skips_directory_markers(self, mock_get_client):
        """Test that download skips S3 directory markers (keys ending with prefix)"""
        # Mock S3 client with directory marker
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': self.test_prefix},  # Directory marker (same as prefix)
                {'Key': f"{self.test_prefix}main.tf"}
            ]
        }
        mock_get_client.return_value = mock_client
        
        # Download files
        result = download_prefix_to_tmp(self.test_bucket, self.test_prefix, self.test_local_path)
        
        # Verify only the actual file was downloaded (not the directory marker)
        self.assertEqual(mock_client.download_file.call_count, 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], os.path.join(self.test_local_path, "main.tf"))


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestS3ServiceGetClient))
    suite.addTests(loader.loadTestsFromTestCase(TestS3ServiceUpload))
    suite.addTests(loader.loadTestsFromTestCase(TestS3ServiceDownload))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
