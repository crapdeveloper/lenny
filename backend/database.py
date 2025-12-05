from config import settings
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Async Engine (only when using async driver)
engine = None
AsyncSessionLocal = None
if "+asyncpg" in settings.DATABASE_URL:
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

# Sync Engine for Celery
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()


async def get_db():
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "AsyncSessionLocal not initialized; use async driver '+asyncpg' in DATABASE_URL."
        )
    async with AsyncSessionLocal() as session:
        yield session
