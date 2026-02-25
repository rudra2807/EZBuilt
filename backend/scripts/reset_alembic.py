import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

async def reset():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    
    async with engine.begin() as conn:
        # Delete the alembic version record
        await conn.execute(text('DELETE FROM alembic_version'))
        print('✅ Reset alembic_version table')
    
    await engine.dispose()
    print('\nNow run: alembic upgrade head')

asyncio.run(reset())
