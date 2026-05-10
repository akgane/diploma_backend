from collections import defaultdict
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from loguru import logger

from app.core.firebase import send_push_notification


BATCH_THRESHOLD = 3


async def send_expiration_notification(db: AsyncIOMotorDatabase) -> None:
    """
    Checks inventory for expiring items and sends notifications.
    Runs as a background task.

    If a user has >= BATCH_THRESHOLD products with pending notifications,
    sends as a single batch push instead of one per product.
    """

    now = datetime.now(timezone.utc)

    cursor = db["inventory_items"].find({
        "status": "active",
        "scheduled_notifications": {
            "$elemMatch": {
                "send_at": {"$lte": now},
                "sent": False
            }
        }
    })
    items = await cursor.to_list(length=10000)

    if not items:
        logger.info("No notifications to send")
        return

    # Group items by user_id
    users_items: dict = defaultdict(list)
    for item in items:
        users_items[item["user_id"]].append(item)

    for user_id, user_items in users_items.items():
        user = await db["users"].find_one({"_id": user_id})
        if not user or not user.get("fcm_token"):
            logger.warning(f"No FCM token for user {user_id}, skipping")
            continue

        # Collect all (item, notification_index) pairs that are due now
        due: list[tuple[dict, int]] = []
        for item in user_items:
            for idx, notification in enumerate(item.get("scheduled_notifications", [])):
                if notification["sent"]:
                    continue
                send_at = notification["send_at"]
                if send_at.tzinfo is None:
                    send_at = send_at.replace(tzinfo=timezone.utc)
                if send_at <= now:
                    due.append((item, idx))

        if not due:
            continue

        if len(user_items) >= BATCH_THRESHOLD:
            await _send_batch(user, user_items, due, now, db)
        else:
            await _send_individual(user, due, now, db)


async def _send_batch(
        user: dict,
        user_items: list[dict],
        due: list[tuple[dict, int]],
        now: datetime,
        db: AsyncIOMotorDatabase,
) -> None:
    """Sends a single grouped push for users with many expiring products."""

    count = len(user_items)
    body = f"{count} products are expiring soon"

    success = await send_push_notification(
        token=user["fcm_token"],
        title="Check your inventory! 🛒",
        body=body,
    )

    if success:
        # Mark only the due notifications as sent
        for item, idx in due:
            await db["inventory_items"].update_one(
                {"_id": item["_id"]},
                {"$set": {f"scheduled_notifications.{idx}.sent": True}},
            )
        logger.info(
            f"Batch notification sent for user {user['_id']}: "
            f"{count} products, {len(due)} notifications marked as sent"
        )


async def _send_individual(
        user: dict,
        due: list[tuple[dict, int]],
        now: datetime,
        db: AsyncIOMotorDatabase,
) -> None:
    """Sends one push per due notification (original behaviour)."""

    for item, idx in due:
        notification = item["scheduled_notifications"][idx]
        threshold = notification["threshold"]
        item_name = item.get("custom_name") or "product"

        if threshold < 1:
            hours = int(threshold * 24)
            time_str = f"{hours} hours"
        elif threshold == 1:
            time_str = "1 day"
        else:
            days = threshold
            time_str = f"{int(days)} days" if days == int(days) else f"{days} days"

        body = f'"{item_name}" expires in {time_str}'

        success = await send_push_notification(
            token=user["fcm_token"],
            title="Check your products! 🛒",
            body=body,
        )

        if success:
            await db["inventory_items"].update_one(
                {"_id": item["_id"]},
                {"$set": {f"scheduled_notifications.{idx}.sent": True}},
            )
            logger.info(
                f"Notification sent for item {item['_id']} threshold {threshold}"
            )