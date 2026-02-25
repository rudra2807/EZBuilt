#!/usr/bin/env python3
"""Clean server startup script"""
import os
import sys
import shutil
from pathlib import Path

def clean_cache():
    """Remove all Python cache files"""
    # Remove all __pycache__ directories
    print("🧹 Cleaning __pycache__ directories...")
    for pycache in Path('.').rglob('__pycache__'):
        shutil.rmtree(pycache, ignore_errors=True)
        print(f"   Removed: {pycache}")

    # Remove .pyc files
    print("🧹 Cleaning .pyc files...")
    for pyc in Path('.').rglob('*.pyc'):
        pyc.unlink(missing_ok=True)

if __name__ == '__main__':
    clean_cache()
    
    print("\n🚀 Starting server...")
    print("=" * 60)

    # Start uvicorn
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[".", "src"]
    )
