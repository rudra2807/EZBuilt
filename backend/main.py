# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import firebase_admin
from firebase_admin import credentials
from src.apis.routes_connection import router as connection_router
from src.apis.routes_requirements import router as requirements_router
from src.apis.routes_terraform import router as terraform_router
from src.apis.routes_auth import router as auth_router
from src.apis.routes_deployment import router as deployment_router

app = FastAPI(title="EZBuilt API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(connection_router)
app.include_router(requirements_router)
app.include_router(terraform_router)
app.include_router(deployment_router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "EZBuilt API",
        "version": "1.0.0"
    }

# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    print("🚀 Starting EZBuilt API Server...")
    print("📍 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (development only)
    )