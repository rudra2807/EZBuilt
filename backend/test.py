from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import subprocess
import tempfile
import os
import json
from datetime import datetime

# One reusable temporary directory for this process
tmp_dir = tempfile.TemporaryDirectory()
path = tmp_dir.name

def generate_terraform(tf_code: str):
    """Write Terraform code to the temp dir and run init/plan."""

    

def read_statefile_from_disk():
    """Helper that reads terraform.tfstate from the temp directory."""
    state_file_path = os.path.join(path, "main.tf")
    if not os.path.exists(state_file_path):
        raise HTTPException(status_code=404, detail="State file not found")

    with open(state_file_path, "r") as f:
        # state_data = json.load(f)
        state_data = f.read()

    return state_data


app = FastAPI(title="EZBuilt API", version="1.0.0")

# CORS etc if you want
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/read")
async def get_statefile():
    """FastAPI route that returns the current terraform state."""
    return read_statefile_from_disk()


if __name__ == "__main__":
    print("🚀 Starting EZBuilt API Server...")
    print("📍 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")

    tf_code = """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_ami" "amazon_linux_2" {
  most_recent = true

  owners = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-2.0.*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = "t2.micro"

  tags = {
    Name        = "web-server"
    ManagedBy   = "EZBuilt"
    Environment = "production"
  }
}

output "instance_id" {
  value = aws_instance.web.id
}
"""

    # Run terraform once at startup
    execute_terraform_init(tf_code=tf_code)

    # Make sure the module path here matches the filename, for example "main:app"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
