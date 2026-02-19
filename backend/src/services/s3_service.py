"""
S3 Service Layer for Terraform File Storage

This module provides functions for uploading and downloading Terraform files
to/from S3, supporting the migration from database BLOB storage to S3-based storage.
"""

import os
import logging
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """Custom exception for S3 service errors"""
    pass


def get_s3_client():
    """
    Create S3 client using boto3 with AWS_REGION from environment.
    
    Returns:
        boto3.client: Configured S3 client
    
    Note:
        Uses default AWS credentials chain (environment variables, IAM role, etc.)
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    logger.debug(f"Creating S3 client for region: {region}")
    return boto3.client("s3", region_name=region)



def upload_terraform_files(bucket: str, prefix: str, files: Dict[str, str]) -> None:
    """
    Upload Terraform files to S3.
    
    Args:
        bucket: S3 bucket name
        prefix: S3 prefix (e.g., "user123/plan456/v1/")
        files: Dict mapping filename to content (e.g., {"main.tf": "..."})
    
    Raises:
        S3ServiceError: If upload fails
    
    Example:
        upload_terraform_files(
            bucket="ezbuilt-terraform-source-dev",
            prefix="user123/plan456/v1/",
            files={"main.tf": "resource \"aws_s3_bucket\" \"example\" {}"}
        )
    """
    client = get_s3_client()
    
    for filename, content in files.items():
        key = f"{prefix}{filename}"
        logger.info(f"Uploading {key} to bucket {bucket}")
        
        try:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                ServerSideEncryption='AES256'
            )
            logger.info(f"Successfully uploaded {key}")
        except (ClientError, NoCredentialsError) as e:
            error_msg = f"Failed to upload {filename}: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg)



def download_prefix_to_tmp(bucket: str, prefix: str, local_path: str) -> List[str]:
    """
    Download all files under S3 prefix to local directory.
    
    Args:
        bucket: S3 bucket name
        prefix: S3 prefix to download from (e.g., "user123/plan456/v1/")
        local_path: Local directory path (e.g., "/tmp/plan123")
    
    Returns:
        List of downloaded file paths
    
    Raises:
        S3ServiceError: If download fails
    
    Example:
        files = download_prefix_to_tmp(
            bucket="ezbuilt-terraform-source-dev",
            prefix="user123/plan456/v1/",
            local_path="/tmp/plan456"
        )
        # Returns: ["/tmp/plan456/main.tf"]
    """
    client = get_s3_client()
    downloaded_files = []
    
    # Ensure local directory exists
    os.makedirs(local_path, exist_ok=True)
    logger.info(f"Created directory: {local_path}")
    
    try:
        # List all objects under prefix
        logger.info(f"Listing objects in s3://{bucket}/{prefix}")
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            error_msg = f"No files found under prefix: {prefix}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg)
        
        # Download each file
        for obj in response['Contents']:
            key = obj['Key']
            # Extract relative path after prefix
            relative_path = key[len(prefix):]
            
            # Skip if it's just the prefix itself (directory marker)
            if not relative_path:
                continue
                
            local_file_path = os.path.join(local_path, relative_path)
            
            # Create subdirectories if needed
            local_file_dir = os.path.dirname(local_file_path)
            if local_file_dir:
                os.makedirs(local_file_dir, exist_ok=True)
            
            logger.info(f"Downloading {key} to {local_file_path}")
            client.download_file(bucket, key, local_file_path)
            downloaded_files.append(local_file_path)
            logger.info(f"Successfully downloaded {key}")
        
        return downloaded_files
        
    except (ClientError, NoCredentialsError) as e:
        error_msg = f"Failed to download files from {prefix}: {str(e)}"
        logger.error(error_msg)
        raise S3ServiceError(error_msg)


def download_terraform_files(bucket: str, prefix: str) -> Dict[str, str]:
    """
    Download Terraform files from S3 and return as dict.
    
    Args:
        bucket: S3 bucket name
        prefix: S3 prefix (e.g., "user123/plan456/v1/")
    
    Returns:
        Dict mapping filename to content (e.g., {"main.tf": "...", "variables.tf": "..."})
    
    Raises:
        S3ServiceError: If download fails
    
    Example:
        files = download_terraform_files(
            bucket="ezbuilt-terraform-source",
            prefix="user123/plan456/v1/"
        )
        # Returns: {"main.tf": "resource ...", "variables.tf": "variable ..."}
    """
    client = get_s3_client()
    files = {}
    
    try:
        # List all objects under prefix
        logger.info(f"Listing objects in s3://{bucket}/{prefix}")
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            logger.warning(f"No files found under prefix: {prefix}")
            return files
        
        # Download each file
        for obj in response['Contents']:
            key = obj['Key']
            # Extract filename after prefix
            filename = key[len(prefix):]
            
            # Skip if it's just the prefix itself (directory marker)
            if not filename:
                continue
            
            logger.info(f"Downloading {key}")
            response_obj = client.get_object(Bucket=bucket, Key=key)
            content = response_obj['Body'].read().decode('utf-8')
            files[filename] = content
            logger.info(f"Successfully downloaded {filename} ({len(content)} bytes)")
        
        return files
        
    except (ClientError, NoCredentialsError) as e:
        error_msg = f"Failed to download files from {prefix}: {str(e)}"
        logger.error(error_msg)
        raise S3ServiceError(error_msg)
