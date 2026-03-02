from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_maker

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Represents async SQLAlchemy session to work with PostgreSQL.
    """
    async with async_session_maker() as session:
        yield session