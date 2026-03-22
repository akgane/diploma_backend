from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

from loguru import logger


class Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


_database = Database()


async def connect_to_mongo() -> None:
    """Connects to MongoDB Atlas. Called on application startup."""
    _database.client = AsyncIOMotorClient(settings.MONGODB_URL, tz_aware=True)
    _database.db = _database.client[settings.MONGODB_DB_NAME]

    await _database.client.admin.command('ping')
    logger.info(f"Successfully connected to MongoDB: [{settings.MONGODB_DB_NAME}]")

    # creating indexes
    await _database.db["products"].create_index("barcode", sparse=True)
    await _database.db["inventory_items"].create_index(
        [("user_id", 1), ("expiration_date", 1)],
    )
    await _database.db["inventory_items"].create_index(
        [("status", 1), ("scheduled_notifications.send_at", 1)]
    )
    await _database.db["recipes"].create_index("spoonacular_id", unique=True)
    await _database.db["ingredient_normalizations"].create_index("raw", unique=True)
    await _database.db["ingredient_normalizations"].create_index("normalized")
    await _database.db["recipe_queries"].create_index("query", unique=True)
    await _database.db["recipe_queries"].create_index("ingredients")
    await _database.db["shopping_list_items"].create_index([("user_id", 1), ("is_checked", 1)])


async def close_mongo_connection() -> None:
    """Closes MongoDB connection. Called on application shutdown."""
    if _database.client is not None:
        _database.client.close()
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Dependency for FastAPI routers"""
    if _database.db is None:
        raise RuntimeError("Database is not initialized. Call connect_to_mongo() first.")
    return _database.db
