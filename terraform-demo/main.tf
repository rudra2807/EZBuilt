# terraform {
#   required_version = ">= 1.5.0"

#   required_providers {
#     aws = {
#       source  = "hashicorp/aws"
#       version = "~> 5.0"
#     }

#     tls = {
#       source  = "hashicorp/tls"
#       version = "~> 4.0"
#     }

#     local = {
#       source  = "hashicorp/local"
#       version = "~> 2.0"
#     }
#   }
# }

# provider "aws" {
#   region = var.aws_region
# }

# # Look up latest Amazon Linux 2 AMI
# data "aws_ami" "amazon_linux_2" {
#   most_recent = true

#   owners = ["amazon"]

#   filter {
#     name   = "name"
#     values = ["amzn2-ami-hvm-2.0.*-x86_64-gp2"]
#   }

#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }
# }

# #################################
# # Networking: VPC and subnet
# #################################

# resource "aws_vpc" "main" {
#   cidr_block           = var.vpc_cidr
#   enable_dns_support   = true
#   enable_dns_hostnames = true

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-vpc"
#     }
#   )
# }

# resource "aws_internet_gateway" "igw" {
#   vpc_id = aws_vpc.main.id

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-igw"
#     }
#   )
# }

# resource "aws_subnet" "public" {
#   vpc_id                  = aws_vpc.main.id
#   cidr_block              = var.public_subnet_cidr
#   map_public_ip_on_launch = true
#   availability_zone       = var.availability_zone

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-public-subnet"
#     }
#   )
# }

# resource "aws_route_table" "public" {
#   vpc_id = aws_vpc.main.id

#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_internet_gateway.igw.id
#   }

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-public-rt"
#     }
#   )
# }

# resource "aws_route_table_association" "public_assoc" {
#   subnet_id      = aws_subnet.public.id
#   route_table_id = aws_route_table.public.id
# }

# #################################
# # Security group for SSH
# #################################

# resource "aws_security_group" "ssh" {
#   name        = "${var.project_name}-ssh-sg"
#   description = "Allow SSH from anywhere"
#   vpc_id      = aws_vpc.main.id

#   ingress {
#     description = "SSH from anywhere"
#     from_port   = 22
#     to_port     = 22
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-ssh-sg"
#     }
#   )
# }

# #################################
# # One PEM key for all EC2 instances
# #################################

# resource "tls_private_key" "ec2_key" {
#   algorithm = "RSA"
#   rsa_bits  = 4096
# }

# resource "aws_key_pair" "ec2_key" {
#   key_name   = "${var.project_name}-keypair"
#   public_key = tls_private_key.ec2_key.public_key_openssh

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-keypair"
#     }
#   )
# }

# resource "local_file" "ec2_key_pem" {
#   content         = tls_private_key.ec2_key.private_key_pem
#   filename        = "${path.module}/${var.project_name}.pem"
#   file_permission = "0400"
# }

# #################################
# # EC2 instance in the public subnet
# #################################

# resource "aws_instance" "web" {
#   ami                    = data.aws_ami.amazon_linux_2.id
#   instance_type          = var.instance_type
#   subnet_id              = aws_subnet.public.id
#   vpc_security_group_ids = [aws_security_group.ssh.id]
#   key_name               = aws_key_pair.ec2_key.key_name

#   metadata_options {
#     http_tokens = "required"
#   }

#   root_block_device {
#     encrypted = true
#   }

#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-ec2-1"
#     }
#   )
# }

provider "aws" {
  region = "us-east-1"
}

# --- Networking Resources ---

# Data source to retrieve the default VPC
data "aws_vpc" "default" {
  default = true
}

# Data source to retrieve a default subnet in us-east-1a
# The Availability Zone is chosen to facilitate EBS volume attachment later.
data "aws_subnet" "default_az1" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = "us-east-1a"
  default_for_az    = true
}

# Security group for Nginx web server
resource "aws_security_group" "nginx_web_server_sg" {
  name        = "nginx-web-server-sg"
  description = "Security group for Nginx web server"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow HTTP traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic by default
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "nginx-web-server-sg"
    Environment = "Development"
    ManagedBy   = "EZBuilt"
  }
}

# --- Other Resources ---

# EC2 Key Pair for SSH access
resource "aws_key_pair" "web_server_key" {
  key_name = "web-server-key"
  # IMPORTANT: Replace the placeholder public_key with your actual public key content.
  # You can generate one using `ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_webserver`
  # and then paste the content of `~/.ssh/id_rsa_webserver.pub` here.
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCjM...YOUR_ACTUAL_PUBLIC_KEY...fQ== generated-key-web-server"

  tags = {
    Name        = "web-server-key"
    Environment = "Development"
    ManagedBy   = "EZBuilt"
  }
}

# --- Compute Resources ---

# Data source to retrieve the latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 instance to host a web server with Nginx
resource "aws_instance" "nginx_web_server" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t2.micro"
  key_name                    = aws_key_pair.web_server_key.key_name
  subnet_id                   = data.aws_subnet.default_az1.id
  vpc_security_group_ids      = [aws_security_group.nginx_web_server_sg.id]
  associate_public_ip_address = true # Assign a public IP for external access

  # User data to install Nginx and start the service
  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              amazon-linux-extras install nginx1 -y
              systemctl start nginx
              systemctl enable nginx
              echo "<h1>Hello from EC2 Nginx Web Server!</h1>" > /usr/share/nginx/html/index.html     
              EOF

  tags = {
    Name        = "nginx-web-server"
    Environment = "Development"
    ManagedBy   = "EZBuilt"
  }
}

# --- Storage Resources ---

# EBS Volume
resource "aws_ebs_volume" "web_server_data_volume" {
  availability_zone = data.aws_subnet.default_az1.availability_zone
  size              = 8
  type              = "gp2"

  tags = {
    Name        = "web-server-data-volume"
    Environment = "Development"
    ManagedBy   = "EZBuilt"
  }
}

# Attach EBS Volume to the EC2 Instance
resource "aws_volume_attachment" "web_server_data_volume_attachment" {
  device_name = "/dev/sdh" # Common device name for secondary volumes
  volume_id   = aws_ebs_volume.web_server_data_volume.id
  instance_id = aws_instance.nginx_web_server.id
}
