from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from loguru import logger

from app.core.firebase import send_push_notification


async def send_expiration_notification(db: AsyncIOMotorDatabase) -> None:
    """
    Checks inventory for expiring items and sends notifications.
    Runs as a background task.
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

    for item in items:
        user = await db["users"].find_one({"_id": item["user_id"]})
        if not user or not user.get("fcm_token"):
            logger.warning(f"No FCM token for user {item['user_id']}, skipping")
            continue

        for idx, notification in enumerate(item.get("scheduled_notifications", [])):
            if notification["sent"]:
                continue

            send_at = notification["send_at"]
            if send_at.tzinfo is None:
                send_at = send_at.replace(tzinfo=timezone.utc)
            if send_at > now:
                continue

            threshold = notification["threshold"]
            item_name = item.get("custom_name") or "product"

            # 0.5 -> 12 hours, 1.0 -> 1 day, 1.5 -> 1.5 days, 3.0 -> 3 days
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
                logger.info(f"Notification sent for item {item['_id']} threshold  {threshold}")