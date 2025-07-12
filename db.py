import asyncpg
from typing import Optional

DB_URL = "postgresql://postgres:tiger@localhost:5432/hospital"

db_pool: Optional[asyncpg.Pool] = None

async def get_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(dsn=DB_URL)
    return db_pool
