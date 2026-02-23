"""
Cleanup script to delete entries from database
Run: python scripts/cleanup_database.py
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

# Extract connection params
url_parts = DATABASE_URL.replace('postgresql+asyncpg://', '').split('@')
user_pass = url_parts[0].split(':')
host_db = url_parts[1].split('/')
host_port = host_db[0].split(':')

USER = user_pass[0]
PASSWORD = user_pass[1]
HOST = host_port[0]
PORT = int(host_port[1]) if len(host_port) > 1 else 5432
DATABASE = host_db[1]

async def cleanup():
    print(f"🔌 Connecting to {HOST}...\n")
    
    try:
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
        
        print("✅ Connected!\n")
        
        # Show current data
        users = await conn.fetch("SELECT user_id, email FROM users")
        integrations = await conn.fetch("SELECT id, user_id, status, external_id FROM aws_integrations")
        
        print(f"📊 Current Data:")
        print(f"   Users: {len(users)}")
        print(f"   AWS Integrations: {len(integrations)}\n")
        
        if not users and not integrations:
            print("✨ Database is already clean!")
            await conn.close()
            return
        
        # Show options
        print("What would you like to delete?")
        print("1. Delete all AWS integrations (keeps users)")
        print("2. Delete all users (also deletes their integrations)")
        print("3. Delete specific user by email")
        print("4. Delete specific integration by external_id")
        print("5. Delete everything (clean slate)")
        print("6. Cancel")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            count = await conn.execute("DELETE FROM aws_integrations")
            print(f"✅ Deleted all AWS integrations")
            
        elif choice == "2":
            count = await conn.execute("DELETE FROM users")
            print(f"✅ Deleted all users (and their integrations)")
            
        elif choice == "3":
            print("\nAvailable users:")
            for user in users:
                print(f"   - {user['email']} (ID: {user['user_id'][:8]}...)")
            email = input("\nEnter email to delete: ").strip()
            count = await conn.execute("DELETE FROM users WHERE email = $1", email)
            if count == "DELETE 1":
                print(f"✅ Deleted user: {email}")
            else:
                print(f"❌ User not found: {email}")
                
        elif choice == "4":
            print("\nAvailable integrations:")
            for integration in integrations:
                print(f"   - {integration['external_id']} (Status: {integration['status']})")
            external_id = input("\nEnter external_id to delete: ").strip()
            count = await conn.execute("DELETE FROM aws_integrations WHERE external_id = $1", external_id)
            if count == "DELETE 1":
                print(f"✅ Deleted integration: {external_id}")
            else:
                print(f"❌ Integration not found: {external_id}")
                
        elif choice == "5":
            confirm = input("⚠️  Delete EVERYTHING? Type 'yes' to confirm: ").strip().lower()
            if confirm == "yes":
                await conn.execute("DELETE FROM aws_integrations")
                await conn.execute("DELETE FROM users")
                print("✅ Deleted everything!")
            else:
                print("❌ Cancelled")
                
        elif choice == "6":
            print("❌ Cancelled")
            
        else:
            print("❌ Invalid choice")
        
        await conn.close()
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup())
