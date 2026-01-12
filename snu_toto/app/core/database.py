from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import DB_SETTINGS
from sqlalchemy.orm import DeclarativeBase


engine = create_async_engine(
    DB_SETTINGS.url,
    pool_recycle=28000,
    pool_size=10,
    max_overflow=20, # 커넥션 풀이 꽉 찼을 때 추가로 허용할 연결 수
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() 
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class Base(DeclarativeBase):
    pass