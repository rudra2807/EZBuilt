import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

async def test_connection():
    database_url = os.getenv("DATABASE_URL")
    print(f"Testing connection to: {database_url}")
    
    # Parse the URL
    # postgresql+asyncpg://postgres:ezbuilt-master@ezbuilt-db.cg5akksckj8j.us-east-1.rds.amazonaws.com:5432/EZBuilt_Database
    parts = database_url.replace("postgresql+asyncpg://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = int(host_port[1])
    database = host_db[1]
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=10
        )
        print("✓ Connection successful!")
        
        # Test query
        version = await conn.fetchval('SELECT version()')
        print(f"PostgreSQL version: {version}")
        
        await conn.close()
        print("✓ Connection closed")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
