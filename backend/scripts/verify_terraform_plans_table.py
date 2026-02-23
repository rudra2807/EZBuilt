"""
Verify terraform_plans table exists with correct schema
Run: python scripts/verify_terraform_plans_table.py
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
    exit(1)

# Extract connection params from URL
url_parts = DATABASE_URL.replace('postgresql+asyncpg://', '').split('@')
user_pass = url_parts[0].split(':')
host_db = url_parts[1].split('/')
host_port = host_db[0].split(':')

USER = user_pass[0]
PASSWORD = user_pass[1]
HOST = host_port[0]
PORT = int(host_port[1]) if len(host_port) > 1 else 5432
DATABASE = host_db[1]

async def verify_table():
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
        
        # Check if terraform_plans table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'terraform_plans'
            )
        """)
        
        if not table_exists:
            print("❌ terraform_plans table does not exist!")
            await conn.close()
            return
        
        print("✅ terraform_plans table exists\n")
        
        # Get column information
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'terraform_plans'
            ORDER BY ordinal_position
        """)
        
        print("📋 Columns:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"   - {col['column_name']}: {col['data_type']} {nullable}{default}")
        print()
        
        # Get indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'terraform_plans'
        """)
        
        print("🔍 Indexes:")
        for idx in indexes:
            print(f"   - {idx['indexname']}")
            print(f"     {idx['indexdef']}")
        print()
        
        # Get foreign keys
        fkeys = await conn.fetch("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'terraform_plans'
        """)
        
        print("🔗 Foreign Keys:")
        for fk in fkeys:
            print(f"   - {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
            print(f"     ON DELETE {fk['delete_rule']}")
        print()
        
        await conn.close()
        print("✅ Verification complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_table())
