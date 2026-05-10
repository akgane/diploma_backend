import asyncio
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging


from loguru import logger

from app.core.config import settings


def init_firebase() -> None:
    # import os
    # print("PATH:", settings.FIREBASE_CREDENTIALS_PATH)
    # print("EXISTS:", os.path.exists(settings.FIREBASE_CREDENTIALS_PATH))

    try:
        firebase_admin.get_app()
        logger.info('Firebase already initialized')
    except ValueError:
        pass

    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH).resolve()

    logger.info(f"Using Firebase credentials: {cred_path}")

    cred = credentials.Certificate(str(cred_path))

    firebase_admin.initialize_app(cred)

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