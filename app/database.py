from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


# PostgreSQL connection string
DATABASE_URL = "postgresql+asyncpg://ecommerce_user:xxxxxxxx@localhost:5432/ecommerce_db"

# Create Engine
async_engine = create_async_engine(DATABASE_URL, echo=True)

# Set up sessions factory
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass
