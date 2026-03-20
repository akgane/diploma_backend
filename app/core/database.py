from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

_database = Database()

async def connect_to_mongo() -> None:
    """Connects to MongoDB Atlas. Called on application startup."""
    _database.client = AsyncIOMotorClient(settings.MONGODB_URL)
    _database.db = _database.client[settings.MONGODB_DB_NAME]

    await _database.client.admin.command('ping')
    print(f"Successfully connected to MongoDB: [{settings.MONGODB_DB_NAME}]")

async def close_mongo_connection() -> None:
    """Closes MongoDB connection. Called on application shutdown."""
    if _database.client is not None:
        _database.client.close()
        print("MongoDB connection closed")

def get_db() -> AsyncIOMotorDatabase:
    """Dependency for FastAPI routers"""
    if _database.db is None:
        raise RuntimeError("Database is not initialized. Call connect_to_mongo() first.")
    return _database.db