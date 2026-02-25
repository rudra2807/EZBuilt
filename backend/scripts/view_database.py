"""
Quick script to view database contents
Run: python scripts/view_database.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

# Parse DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env.local")
    print("Please add: DATABASE_URL=postgresql+asyncpg://postgres:your-password@your-endpoint:5432/ezbuilt")
    exit(1)

# Extract connection params from URL
# Format: postgresql+asyncpg://user:pass@host:port/database
url_parts = DATABASE_URL.replace('postgresql+asyncpg://', '').split('@')
user_pass = url_parts[0].split(':')
host_db = url_parts[1].split('/')
host_port = host_db[0].split(':')

USER = user_pass[0]
PASSWORD = user_pass[1]
HOST = host_port[0]
PORT = int(host_port[1]) if len(host_port) > 1 else 5432
DATABASE = host_db[1]

async def view_database():
    print(f"🔌 Connecting to {HOST}...")
    
    try:
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
        
        print("✅ Connected successfully!\n")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if not tables:
            print("⚠️  No tables found. Run migrations first:")
            print("   cd backend")
            print("   alembic revision --autogenerate -m 'Initial schema'")
            print("   alembic upgrade head")
            await conn.close()
            return
        
        print("📊 Tables:")
        for table in tables:
            print(f"   - {table['table_name']}")
        print()
        
        # View users
        users = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC LIMIT 10")
        print(f"👥 Users ({len(users)}):")
        if users:
            for user in users:
                print(f"   - {user['email']} (ID: {user['user_id'][:8]}...)")
                print(f"     Created: {user['created_at']}")
                print(f"     Last login: {user['last_login']}")
                print()
        else:
            print("   No users yet\n")
        
        # View AWS integrations
        integrations = await conn.fetch("""
            SELECT ai.*, u.email 
            FROM aws_integrations ai
            JOIN users u ON ai.user_id = u.user_id
            ORDER BY ai.created_at DESC 
            LIMIT 10
        """)
        print(f"🔗 AWS Integrations ({len(integrations)}):")
        if integrations:
            for integration in integrations:
                print(f"   - {integration['email']}")
                print(f"     Status: {integration['status']}")
                print(f"     External ID: {integration['external_id']}")
                print(f"     Role ARN: {integration['role_arn'] or 'Not set'}")
                print(f"     Created: {integration['created_at']}")
                print()
        else:
            print("   No integrations yet\n")
        
        await conn.close()
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Aurora endpoint is correct")
        print("2. Verify security group allows your IP (port 5432)")
        print("3. Confirm database 'ezbuilt' exists")
        print("4. Check credentials are correct")

if __name__ == "__main__":
    asyncio.run(view_database())
