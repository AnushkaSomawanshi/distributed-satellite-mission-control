import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.database.models import Base
from backend.config import settings

# Hybrid database engine support (SQLite async by default for simple zero-dependency local run, Postgres async if configured)
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Synchronous fallback engine for local sync helpers
sync_db_url = settings.DATABASE_URL
if sync_db_url.startswith("sqlite+aiosqlite://"):
    sync_db_url = sync_db_url.replace("sqlite+aiosqlite://", "sqlite://")
elif sync_db_url.startswith("postgresql+asyncpg://"):
    sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

try:
    sync_engine = create_engine(sync_db_url, echo=False)
    SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
    Base.metadata.create_all(bind=sync_engine)
except Exception:
    sync_engine = None
    SyncSessionLocal = None


@contextmanager
def get_db_context():
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

