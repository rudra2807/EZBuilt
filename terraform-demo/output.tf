output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID of the SSH security group"
  value       = aws_security_group.ssh.id
}

output "ec2_instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.web.id
}

output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.web.public_ip
}

output "pem_file_path" {
  description = "Path to the generated PEM file"
  value       = local_file.ec2_key_pem.filename
}

output "ssh_command_example" {
  description = "Example SSH command to connect to the EC2 instance"
  value       = "ssh -i ${local_file.ec2_key_pem.filename} ec2-user@${aws_instance.web.public_ip}"
}
