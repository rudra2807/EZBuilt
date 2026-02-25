# Terraform State Management

## Overview

The system now properly manages Terraform state files for deployment and destroy operations.

## Apply Flow (Deployment)

1. Download Terraform files (.tf files) from S3
2. Run `terraform init`
3. Run `terraform plan`
4. Run `terraform apply`
5. **Upload `terraform.tfstate` to S3** (NEW)
6. Update deployment status to SUCCESS
7. Clean up temp directory

### State File Upload

After a successful apply:

- The `terraform.tfstate` file is read from the temp directory
- Uploaded to S3 at the same prefix as the .tf files
- Stored alongside: `main.tf`, `variables.tf`, `outputs.tf`
- If upload fails, deployment is still marked as successful (state upload is best-effort)

## Destroy Flow

1. Query database to get terraform_plan_id
2. Query terraform_plan to get s3_prefix
3. **Download ALL files from S3** (including terraform.tfstate)
4. Assume AWS role
5. Run `terraform init` (reads terraform.tfstate)
6. Run `terraform destroy` (uses state to know what to destroy)
7. Update deployment status to DESTROYED
8. Clean up temp directory

### Why This Works

- Terraform needs the state file to know what resources exist
- By downloading the state file from S3, Terraform can properly destroy all resources
- Without the state file, Terraform would report "No changes. No objects need to be destroyed."

## S3 Structure

```
s3://ezbuilt-terraform-source/
  └── {user_id}/
      └── {plan_id}/
          └── v1/
              ├── main.tf
              ├── variables.tf
              ├── outputs.tf
              └── terraform.tfstate  (added after successful apply)
```

## Error Handling

### Apply

- If state upload fails: Log error but don't fail the deployment
- Deployment is marked as SUCCESS
- User can still manually destroy resources via AWS console

### Destroy

- If state file doesn't exist in S3: Terraform will report no resources to destroy
- If S3 download fails: Destroy operation fails with clear error message
- If terraform init fails: Destroy operation fails
- If terraform destroy fails: Status set to DESTROY_FAILED with error details

## Platform Compatibility

- Uses `tempfile.gettempdir()` on Windows
- Uses `/tmp` on Linux/Unix
- Paths constructed with `os.path.join()` for cross-platform compatibility

## Future Improvements

1. **Remote State Backend**: Consider using S3 as a remote backend instead of local state
2. **State Locking**: Implement state locking with DynamoDB to prevent concurrent modifications
3. **State Versioning**: Enable S3 versioning on the bucket to keep state history
4. **State Encryption**: Ensure state files are encrypted at rest (currently using AES256)
