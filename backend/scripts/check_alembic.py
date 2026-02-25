import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

async def check():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    
    async with engine.connect() as conn:
        # Check alembic version
        result = await conn.execute(text('SELECT version_num FROM alembic_version'))
        version = result.scalar()
        print(f'Current alembic version: {version}')
        
        # Check tables
        result2 = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [row[0] for row in result2]
        print(f'\nTables in database:')
        for table in tables:
            print(f'  - {table}')
    
    await engine.dispose()

asyncio.run(check())
