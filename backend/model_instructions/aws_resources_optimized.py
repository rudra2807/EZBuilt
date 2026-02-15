"""
AWS Resources and Data Sources - Curated for EZBuilt MVP

This file contains a focused subset of the 1,526 AWS resources and 608 data sources
that are most relevant for common infrastructure patterns.

Strategy:
1. Include only the most commonly used resources for web apps, APIs, and databases
2. Keep the prompt token count manageable
3. Allow the LLM to focus on core infrastructure patterns

Full lists available:
- data_sources_list: 608 data sources
- resources_schema_list: 1,526 resources
"""

# CORE DATA SOURCES (Most commonly used)
CORE_DATA_SOURCES = [
    # Networking
    "aws_vpc",
    "aws_subnet",
    "aws_subnets",
    "aws_security_group",
    "aws_security_groups",
    "aws_availability_zones",
    "aws_availability_zone",
    
    # Compute
    "aws_ami",
    "aws_ami_ids",
    "aws_instance",
    "aws_instances",
    "aws_launch_template",
    
    # Load Balancing
    "aws_lb",
    "aws_alb",
    "aws_lb_target_group",
    "aws_alb_target_group",
    "aws_lb_listener",
    "aws_alb_listener",
    
    # Database
    "aws_db_instance",
    "aws_db_subnet_group",
    "aws_rds_cluster",
    "aws_dynamodb_table",
    
    # Storage
    "aws_s3_bucket",
    "aws_s3_bucket_object",
    "aws_s3_objects",
    
    # Serverless
    "aws_lambda_function",
    "aws_lambda_layer_version",
    "aws_api_gateway_rest_api",
    "aws_apigatewayv2_api",
    
    # IAM
    "aws_iam_role",
    "aws_iam_policy",
    "aws_iam_policy_document",
    "aws_caller_identity",
    
    # ECS/Containers
    "aws_ecs_cluster",
    "aws_ecs_task_definition",
    "aws_ecs_service",
    
    # Cache & Queue
    "aws_elasticache_cluster",
    "aws_sqs_queue",
    
    # Other utilities
    "aws_region",
    "aws_partition",
]

# CORE RESOURCES (Most commonly used)
CORE_RESOURCES = [
    # Networking
    "aws_vpc",
    "aws_subnet",
    "aws_internet_gateway",
    "aws_nat_gateway",
    "aws_eip",
    "aws_route_table",
    "aws_route_table_association",
    "aws_route",
    "aws_security_group",
    "aws_security_group_rule",
    "aws_network_interface",
    
    # Compute - EC2
    "aws_instance",
    "aws_key_pair",
    "aws_launch_template",
    "aws_autoscaling_group",
    "aws_autoscaling_policy",
    "aws_autoscaling_schedule",
    
    # Load Balancing
    "aws_lb",
    "aws_alb",
    "aws_lb_target_group",
    "aws_alb_target_group",
    "aws_lb_target_group_attachment",
    "aws_alb_target_group_attachment",
    "aws_lb_listener",
    "aws_alb_listener",
    "aws_lb_listener_rule",
    "aws_alb_listener_rule",
    
    # Database - RDS
    "aws_db_instance",
    "aws_db_subnet_group",
    "aws_db_parameter_group",
    "aws_db_option_group",
    "aws_rds_cluster",
    "aws_rds_cluster_instance",
    
    # Database - DynamoDB
    "aws_dynamodb_table",
    "aws_dynamodb_table_item",
    
    # Storage - S3
    "aws_s3_bucket",
    "aws_s3_bucket_public_access_block",
    "aws_s3_bucket_website_configuration",
    "aws_s3_bucket_policy",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_object",
    
    # Storage - EBS
    "aws_ebs_volume",
    "aws_volume_attachment",
    
    # Serverless - Lambda
    "aws_lambda_function",
    "aws_lambda_permission",
    "aws_lambda_layer_version",
    "aws_lambda_event_source_mapping",
    
    # API Gateway
    "aws_api_gateway_rest_api",
    "aws_api_gateway_resource",
    "aws_api_gateway_method",
    "aws_api_gateway_integration",
    "aws_api_gateway_deployment",
    "aws_api_gateway_stage",
    "aws_apigatewayv2_api",
    "aws_apigatewayv2_integration",
    "aws_apigatewayv2_route",
    "aws_apigatewayv2_stage",
    
    # IAM
    "aws_iam_role",
    "aws_iam_role_policy",
    "aws_iam_role_policy_attachment",
    "aws_iam_policy",
    "aws_iam_instance_profile",
    
    # ECS/Containers
    "aws_ecs_cluster",
    "aws_ecs_task_definition",
    "aws_ecs_service",
    "aws_ecs_capacity_provider",
    "aws_ecr_repository",
    
    # Cache - ElastiCache
    "aws_elasticache_cluster",
    "aws_elasticache_subnet_group",
    "aws_elasticache_parameter_group",
    "aws_elasticache_replication_group",
    
    # Queue - SQS
    "aws_sqs_queue",
    "aws_sqs_queue_policy",
    
    # Monitoring
    "aws_cloudwatch_log_group",
    "aws_cloudwatch_log_stream",
    "aws_cloudwatch_metric_alarm",
    
    # CloudFront (for static sites)
    "aws_cloudfront_distribution",
    "aws_cloudfront_origin_access_identity",
    
    # Secrets Management
    "aws_secretsmanager_secret",
    "aws_secretsmanager_secret_version",
    
    # Utility resources (not AWS)
    "random_password",
    "random_id",
    "tls_private_key",
    "local_file",
    "local_sensitive_file",
]


def load_full_lists():
    """Load the complete lists from the uploaded files"""
    import json
    
    with open('/mnt/user-data/uploads/data_sources_list', 'r', encoding='utf-16') as f:
        all_data_sources = json.load(f)
    
    with open('/mnt/user-data/uploads/resources_schema_list', 'r', encoding='utf-16') as f:
        all_resources = json.load(f)
    
    return all_data_sources, all_resources


def get_data_sources_for_prompt():
    """
    Returns a string listing allowed data sources for the LLM prompt.
    Uses curated list for MVP to keep prompt size manageable.
    """
    return """
Available AWS Data Sources (curated for common use cases):

NETWORKING:
- aws_vpc: Query VPC by ID or get default VPC
- aws_subnet: Get subnet details by ID
- aws_subnets: List subnets in a VPC
- aws_security_group: Get security group details
- aws_availability_zones: List available AZs in region

COMPUTE:
- aws_ami: Find AMI images (use for latest Amazon Linux, Ubuntu, etc.)
- aws_instance: Get EC2 instance details
- aws_launch_template: Query launch templates

LOAD BALANCING:
- aws_lb / aws_alb: Query load balancers
- aws_lb_target_group / aws_alb_target_group: Query target groups
- aws_lb_listener / aws_alb_listener: Query listeners

DATABASE:
- aws_db_instance: Query RDS instances
- aws_db_subnet_group: Query DB subnet groups
- aws_dynamodb_table: Query DynamoDB tables

STORAGE:
- aws_s3_bucket: Query S3 buckets
- aws_s3_object / aws_s3_objects: Query S3 objects

SERVERLESS:
- aws_lambda_function: Query Lambda functions
- aws_api_gateway_rest_api: Query REST APIs
- aws_apigatewayv2_api: Query HTTP APIs

IAM:
- aws_iam_role: Query IAM roles
- aws_iam_policy: Query IAM policies
- aws_caller_identity: Get current AWS account info

CONTAINERS:
- aws_ecs_cluster: Query ECS clusters
- aws_ecs_task_definition: Query task definitions

CACHE & QUEUE:
- aws_elasticache_cluster: Query ElastiCache clusters
- aws_sqs_queue: Query SQS queues

UTILITIES:
- aws_region: Get current region info
- aws_availability_zones: List AZs

Usage patterns:
1. Use data sources to query existing resources (like default VPC)
2. Use data sources to get latest AMI IDs
3. Use data sources to reference resources created outside Terraform

Example:
data "aws_vpc" "default" {
  default = true
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}
"""


def get_resources_for_prompt():
    """
    Returns a string listing allowed resources for the LLM prompt.
    Uses curated list for MVP to keep prompt size manageable.
    """
    return """
Available AWS Resources (curated for common use cases):

NETWORKING RESOURCES:
- aws_vpc: Create VPC with CIDR block
- aws_subnet: Create subnet in VPC
- aws_internet_gateway: Create internet gateway
- aws_nat_gateway: Create NAT gateway (requires EIP)
- aws_eip: Allocate Elastic IP
- aws_route_table: Create route table
- aws_route_table_association: Associate route table with subnet
- aws_security_group: Create security group with ingress/egress rules

COMPUTE RESOURCES - EC2:
- aws_instance: Launch EC2 instance
- aws_key_pair: Register SSH key pair
- aws_launch_template: Create launch template for ASG
- aws_autoscaling_group: Create auto-scaling group
- aws_autoscaling_policy: Create scaling policies

LOAD BALANCING RESOURCES:
- aws_lb / aws_alb: Create Application Load Balancer
- aws_lb_target_group / aws_alb_target_group: Create target group
- aws_lb_target_group_attachment: Attach instances to target group
- aws_lb_listener / aws_alb_listener: Create ALB listener
- aws_lb_listener_rule / aws_alb_listener_rule: Create routing rules

DATABASE RESOURCES - RDS:
- aws_db_instance: Create RDS database instance
- aws_db_subnet_group: Create DB subnet group
- aws_db_parameter_group: Create DB parameter group

DATABASE RESOURCES - DYNAMODB:
- aws_dynamodb_table: Create DynamoDB table

STORAGE RESOURCES - S3:
- aws_s3_bucket: Create S3 bucket
- aws_s3_bucket_website_configuration: Configure static website hosting
- aws_s3_bucket_public_access_block: Configure public access settings
- aws_s3_bucket_policy: Attach bucket policy
- aws_s3_bucket_versioning: Enable versioning
- aws_s3_object: Upload object to S3

SERVERLESS RESOURCES - LAMBDA:
- aws_lambda_function: Create Lambda function
- aws_lambda_permission: Grant invoke permissions
- aws_lambda_layer_version: Create Lambda layer

API GATEWAY RESOURCES:
- aws_api_gateway_rest_api: Create REST API (older, more complex)
- aws_apigatewayv2_api: Create HTTP API (simpler, recommended)
- aws_apigatewayv2_integration: Create integration with Lambda
- aws_apigatewayv2_route: Create route
- aws_apigatewayv2_stage: Create stage

IAM RESOURCES:
- aws_iam_role: Create IAM role
- aws_iam_role_policy_attachment: Attach managed policy to role
- aws_iam_policy: Create custom IAM policy
- aws_iam_instance_profile: Create instance profile for EC2

CONTAINER RESOURCES - ECS:
- aws_ecs_cluster: Create ECS cluster
- aws_ecs_task_definition: Define ECS task
- aws_ecs_service: Create ECS service (Fargate or EC2)
- aws_ecr_repository: Create container registry

CACHE RESOURCES - ELASTICACHE:
- aws_elasticache_cluster: Create Redis or Memcached cluster
- aws_elasticache_subnet_group: Create ElastiCache subnet group

QUEUE RESOURCES - SQS:
- aws_sqs_queue: Create SQS queue

MONITORING RESOURCES:
- aws_cloudwatch_log_group: Create CloudWatch log group
- aws_cloudwatch_metric_alarm: Create metric alarm

CDN RESOURCES:
- aws_cloudfront_distribution: Create CloudFront distribution

SECRETS MANAGEMENT:
- aws_secretsmanager_secret: Create secret
- aws_secretsmanager_secret_version: Set secret value

UTILITY RESOURCES (Non-AWS providers):
- random_password: Generate random password (for DB credentials)
- tls_private_key: Generate SSH key pair
- local_file: Write file locally
- local_sensitive_file: Write sensitive file locally (e.g., SSH keys)

Note: This is a curated subset of 1,526+ available AWS resources.
Focus on these common patterns for the MVP. Additional resources can be
added as needed for more advanced use cases.
"""


def get_combined_schema_string():
    """
    Returns a combined string with both data sources and resources
    formatted for injection into the Phase 2 prompt.
    """
    return f"""
=====================================
ALLOWED DATA SOURCES
=====================================

{get_data_sources_for_prompt()}

=====================================
ALLOWED RESOURCES
=====================================

{get_resources_for_prompt()}

IMPORTANT RESTRICTIONS:
1. Only use data sources and resources listed above
2. Do not invent resource names or types not in these lists
3. If a required resource is not listed, use the closest available alternative and document the choice
4. For advanced use cases beyond these resources, add a note in "warnings" that manual intervention may be needed
"""


if __name__ == "__main__":
    # Show statistics
    all_data_sources, all_resources = load_full_lists()
    
    print("=" * 70)
    print("AWS RESOURCES & DATA SOURCES - STATISTICS")
    print("=" * 70)
    print(f"\nTotal available data sources: {len(all_data_sources)}")
    print(f"Curated data sources for MVP:  {len(CORE_DATA_SOURCES)}")
    print(f"Coverage: {len(CORE_DATA_SOURCES) / len(all_data_sources) * 100:.1f}%")
    
    print(f"\nTotal available resources:     {len(all_resources)}")
    print(f"Curated resources for MVP:     {len(CORE_RESOURCES)}")
    print(f"Coverage: {len(CORE_RESOURCES) / len(all_resources) * 100:.1f}%")
    
    print("\n" + "=" * 70)
    print("RATIONALE")
    print("=" * 70)
    print("""
Including all 1,526 resources and 608 data sources in the prompt would:
1. Consume excessive tokens (30,000+ tokens just for the lists)
2. Confuse the LLM with too many options
3. Slow down generation time
4. Increase costs

The curated list focuses on:
- Common web application patterns (80% of use cases)
- Database and caching solutions
- Serverless and container compute
- Networking fundamentals
- Load balancing and CDN

This covers the EZBuilt MVP scope while keeping the prompt efficient.
    """)
    
    print("\nCurated Data Sources:")
    for ds in CORE_DATA_SOURCES:
        print(f"  ✓ {ds}")
    
    print(f"\nCurated Resources (showing first 20 of {len(CORE_RESOURCES)}):")
    for r in CORE_RESOURCES[:20]:
        print(f"  ✓ {r}")
    print(f"  ... and {len(CORE_RESOURCES) - 20} more")