#!/usr/bin/env python3
"""
test_integration.py - Integration test script for EZBuilt
Tests the complete flow from account connection to deployment
"""

import requests
import time
import json
from typing import Optional

BASE_URL = "http://localhost:8000"
USER_ID = "test-user-123"

class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(step: str, message: str):
    """Print a step with formatting"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{step}{Colors.ENDC} {message}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")

def test_server_health():
    """Test if server is running"""
    print_step("0️⃣", "Testing server connection...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print_success("Server is running!")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Failed to connect to server: {str(e)}")
        print_info("Make sure the server is running with: python backend/main.py")
        return False

def step1_generate_cfn_link() -> Optional[dict]:
    """Step 1: Generate CloudFormation link"""
    print_step("1️⃣", "Generating CloudFormation link...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/generate-cfn-link",
            json={"user_id": USER_ID}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("CloudFormation link generated!")
            print_info(f"External ID: {data['external_id']}")
            print_info(f"CFN Link: {data['cfn_link'][:80]}...")
            return data
        else:
            print_error(f"Failed: {response.json()}")
            return None
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def step2_manual_connection(external_id: str) -> bool:
    """Step 2: Simulate manual connection"""
    print_step("2️⃣", "Simulating AWS account connection...")
    print_warning("In production, user would:")
    print("   1. Click the CloudFormation link")
    print("   2. Create the stack in AWS")
    print("   3. Copy the Role ARN from outputs")
    print("   4. Paste it in the platform")
    
    print("\n" + "="*60)
    print("For testing purposes, enter a dummy Role ARN:")
    print("Example: arn:aws:iam::123456789012:role/EZBuilt-DeploymentRole-abc123")
    print("="*60)
    
    role_arn = input("\nRole ARN: ").strip()
    
    if not role_arn:
        print_error("Role ARN is required")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/connect-account-manual",
            params={
                "user_id": USER_ID,
                "role_arn": role_arn,
                "external_id": external_id
            }
        )
        
        if response.status_code == 200:
            print_success("Account connected successfully!")
            print_info(f"Response: {response.json()}")
            return True
        else:
            error = response.json()
            print_error(f"Connection failed: {error.get('detail', 'Unknown error')}")
            return False
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def step3_generate_terraform() -> Optional[dict]:
    """Step 3: Generate Terraform code"""
    print_step("3️⃣", "Generating Terraform code...")
    
    print("\n" + "="*60)
    print("Describe your infrastructure requirements:")
    print("Example: I need a web server with nginx and a PostgreSQL database")
    print("="*60)
    
    requirements = input("\nRequirements: ").strip()
    
    if not requirements:
        print_error("Requirements are required")
        return None
    
    try:
        print_info("Calling AI model to generate Terraform...")
        response = requests.post(
            f"{BASE_URL}/api/generate-terraform",
            json={
                "user_id": USER_ID,
                "requirements": requirements
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'error':
                print_error(f"Generation failed: {data.get('message', 'Unknown error')}")
                if 'errors' in data:
                    print(f"\nErrors:\n{data['errors']}")
                return None
            
            print_success("Terraform code generated!")
            print_info(f"Terraform ID: {data['terraform_id']}")
            print("\n" + "="*60)
            print("Generated Terraform Code:")
            print("="*60)
            print(data['code'])
            print("="*60)
            
            return data
        else:
            print_error(f"Failed: {response.json()}")
            return None
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def step4_deploy(terraform_id: str) -> Optional[str]:
    """Step 4: Deploy Terraform"""
    print_step("4️⃣", "Deploying Terraform to AWS...")
    
    print("\n" + "="*60)
    confirm = input("Ready to deploy? (yes/no): ").strip().lower()
    print("="*60)
    
    if confirm != 'yes':
        print_warning("Deployment cancelled")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/deploy",
            json={
                "user_id": USER_ID,
                "terraform_id": terraform_id
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Deployment started!")
            print_info(f"Deployment ID: {data['deployment_id']}")
            return data['deployment_id']
        else:
            error = response.json()
            print_error(f"Deployment failed: {error.get('detail', 'Unknown error')}")
            return None
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def step5_monitor_deployment(deployment_id: str):
    """Step 5: Monitor deployment status"""
    print_step("5️⃣", "Monitoring deployment...")
    
    max_attempts = 60  # 3 minutes with 3-second intervals
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"{BASE_URL}/api/deployment/{deployment_id}/status"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data['status']
                
                print(f"\rStatus: {status.upper()}", end='', flush=True)
                
                if status in ['success', 'failed']:
                    print()  # New line
                    if status == 'success':
                        print_success("Deployment completed successfully!")
                    else:
                        print_error("Deployment failed!")
                    
                    print("\n" + "="*60)
                    print("Deployment Output:")
                    print("="*60)
                    print(data['output'])
                    print("="*60)
                    break
            
            time.sleep(3)
            attempt += 1
        
        except Exception as e:
            print_error(f"\nError checking status: {str(e)}")
            break
    
    if attempt >= max_attempts:
        print_warning("\nDeployment monitoring timeout")

def step6_destroy_infrastructure(terraform_id: str) -> Optional[str]:
    """Step 6: Destroy infrastructure"""
    print_step("6️⃣", "Destroying infrastructure...")
    
    print("\n" + "="*60)
    print_warning("⚠️  This will destroy all deployed resources!")
    confirm = input("Are you sure you want to destroy? (yes/no): ").strip().lower()
    print("="*60)
    
    if confirm != 'yes':
        print_warning("Destroy cancelled")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/destroy",
            json={
                "user_id": USER_ID,
                "terraform_id": terraform_id
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Destroy operation started!")
            print_info(f"Deployment ID: {data['deployment_id']}")
            return data['deployment_id']
        else:
            error = response.json()
            print_error(f"Destroy failed: {error.get('detail', 'Unknown error')}")
            return None
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def step7_monitor_destroy(deployment_id: str):
    """Step 7: Monitor destroy status"""
    print_step("7️⃣", "Monitoring destroy operation...")
    
    max_attempts = 60  # 3 minutes with 3-second intervals
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"{BASE_URL}/api/deployment/{deployment_id}/status"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data['status']
                
                print(f"\rStatus: {status.upper()}", end='', flush=True)
                
                if status in ['destroyed', 'destroy_failed']:
                    print()  # New line
                    if status == 'destroyed':
                        print_success("Infrastructure destroyed successfully!")
                    else:
                        print_error("Destroy operation failed!")
                    
                    print("\n" + "="*60)
                    print("Destroy Output:")
                    print("="*60)
                    print(data['output'])
                    print("="*60)
                    break
            
            time.sleep(3)
            attempt += 1
        
        except Exception as e:
            print_error(f"\nError checking status: {str(e)}")
            break
    
    if attempt >= max_attempts:
        print_warning("\nDestroy monitoring timeout")

def run_full_test():
    """Run complete integration test"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("🚀 EZBuilt Integration Test")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    # Step 0: Check server
    if not test_server_health():
        return
    
    # Step 1: Generate CFN link
    cfn_data = step1_generate_cfn_link()
    if not cfn_data:
        return
    
    # Step 2: Manual connection
    if not step2_manual_connection(cfn_data['external_id']):
        print_warning("\nSkipping deployment steps due to connection failure")
        print_info("This is expected if you don't have AWS credentials configured")
        return
    
    # Step 3: Generate Terraform
    tf_data = step3_generate_terraform()
    if not tf_data:
        return
    
    # Step 4: Deploy
    deployment_id = step4_deploy(tf_data['terraform_id'])
    if not deployment_id:
        return
    
    # Step 5: Monitor deployment
    step5_monitor_deployment(deployment_id)
    
    # Step 6: Ask if user wants to destroy
    print("\n" + "="*60)
    test_destroy = input("\nWould you like to test destroy functionality? (yes/no): ").strip().lower()
    
    if test_destroy == 'yes':
        destroy_deployment_id = step6_destroy_infrastructure(tf_data['terraform_id'])
        if destroy_deployment_id:
            # Step 7: Monitor destroy
            step7_monitor_destroy(destroy_deployment_id)
    
    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*60}")
    print("✅ Integration test completed!")
    print(f"{'='*60}{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        run_full_test()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print_error(f"\nUnexpected error: {str(e)}")