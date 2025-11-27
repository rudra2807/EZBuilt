# variable "project_name" {
#   description = "Base name for tagging and resource naming"
#   type        = string
#   default     = "demo-ec2-vpc"
# }

# variable "aws_region" {
#   description = "AWS region where resources will be created"
#   type        = string
#   default     = "us-east-1"
# }

# # VPC CIDR. Using /28 which is the smallest allowed by AWS.
# variable "vpc_cidr" {
#   description = "CIDR block for the VPC"
#   type        = string
#   default     = "10.0.0.0/28"
# }

# # Public subnet CIDR inside the VPC. Also /28.
# variable "public_subnet_cidr" {
#   description = "CIDR block for the public subnet"
#   type        = string
#   default     = "10.0.0.0/28"
# }

# variable "availability_zone" {
#   description = "Availability zone for the public subnet"
#   type        = string
#   default     = "us-east-1a"
# }

# variable "instance_type" {
#   description = "EC2 instance type"
#   type        = string
#   default     = "t2.micro"
# }

# variable "tags" {
#   description = "Common tags applied to all taggable resources"
#   type        = map(string)
#   default = {
#     Environment = "dev"
#     ManagedBy   = "terraform"
#   }
# }
