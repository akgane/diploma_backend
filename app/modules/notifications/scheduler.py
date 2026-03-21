import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase

from loguru import logger

from app.modules.notifications.service import send_expiration_notification

CHECK_INTERVAL_MINUTES = 15

async def start_notification_scheduler(db: AsyncIOMotorDatabase) -> None:
    """
    Background loop that runs expiration check every XX hours.
    Started via lifespan in main.py
    """

    logger.info("Notification scheduler started")
    while True:
        try:
            logger.info("Running expiration check...")
            await send_expiration_notification(db)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)