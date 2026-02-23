import asyncio
import sys
from src.database.connection import get_db

async def test_connection():
    try:
        print("Testing database connection...")
        async for session in get_db():
            print("✓ Database connection successful!")
            print(f"Session: {session}")
            break
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connection())
