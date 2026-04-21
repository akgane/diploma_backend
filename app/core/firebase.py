import asyncio

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

from loguru import logger

def init_firebase() -> None:
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()
    # if not firebase_admin._apps:
    #     cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    #     firebase_admin.initialize_app(cred)
    logger.info("Firebase initialized")

async def send_push_notification(token: str, title: str, body: str) -> bool:
    """
    Sends push notification to a specific device token.
    :return: True if successful, False otherwise
    """

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )

    try:
        await asyncio.to_thread(messaging.send, message)
        logger.info(f"Notification sent to token: {token[:20]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False