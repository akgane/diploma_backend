import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase

from loguru import logger

from app.core.database import get_db
from app.modules.notifications.service import send_expiration_notification

CHECK_INTERVAL_MINUTES = 15

async def start_notification_scheduler() -> None:
    """
    Background loop that runs expiration check every XX minutes.
    Started via lifespan in main.py
    """

    logger.info("Notification scheduler started")
    while True:
        try:
            db = get_db()
            logger.info("Running expiration check...")
            await send_expiration_notification(db)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)