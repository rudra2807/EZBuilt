from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import boto3
import subprocess
import tempfile
import os
import json
from typing import Optional
from datetime import datetime
import uuid

users_db = {}
terraform_db = {}
deployments_db = {}
connections_db = {}

def save_role_arn(user_id: str, role_arn: str):
    """Save role ARN to user record"""
    if user_id not in users_db:
        users_db[user_id] = {}
    
    users_db[user_id]['role_arn'] = role_arn
    users_db[user_id]['connected_at'] = datetime.utcnow().isoformat()
    
    # Update connection status
    for external_id, conn in connections_db.items():
        if conn['user_id'] == user_id:
            connections_db[external_id]['status'] = 'connected'
            connections_db[external_id]['role_arn'] = role_arn

def assume_role(role_arn: str, external_id: str):
    """Assume role in user's AWS account"""
    sts = boto3.client('sts')
    
    try:
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='EZBuilt-Session',
            ExternalId=external_id,
            DurationSeconds=3600
        )
        return response['Credentials']
    except Exception as e:
        raise Exception(f"Failed to assume role: {str(e)}")

# ============================================
# API ENDPOINTS
# ============================================
app = FastAPI(
    title="EZBuilt API",
    description="Backend API for EZBuilt - Simplified Cloud Infrastructure Deployment",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "EZBuilt API",
        "version": "1.0.0"
    }

@app.post("/api/connect-account-manual")
async def connect_account_manual(user_id: str, role_arn: str, external_id: str):
    """
    Manual connection method (for MVP without callback)
    User provides role ARN directly
    """
    try:
        # Test assume role
        assume_role(role_arn, external_id)
        
        # Save connection
        save_role_arn(user_id, role_arn)
        
        return {
            "status": "success",
            "message": "AWS account connected successfully",
            "role_arn": role_arn
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting EZBuilt API Server...")
    print("📍 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        "test:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (development only)
    )