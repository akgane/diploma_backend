from datetime import datetime, timezone, timedelta

from bson import ObjectId


def build_scheduled_notifications(
        expiration_date: datetime,
        thresholds: list[float]
) -> list[dict]:
    """
    Builds scheduled notifications list based on expiration date and thresholds.
    Skips thresholds where send_at is in the past
    """
    now = datetime.now(timezone.utc)
    scheduled = []

    for threshold in thresholds:
        send_at = expiration_date - timedelta(days=threshold)
        if send_at > now:
            scheduled.append({
                "threshold": threshold,
                "send_at": send_at,
                "sent": False
            })
    return scheduled


def build_inventory_document(
        user_id: ObjectId,
        expiration_date: datetime,
        amount: float,
        unit: str,
        scheduled_notifications: list[dict],
        product_id: ObjectId | None = None,
        barcode: str | None = None,
        custom_name: str | None = None,
        category: str | None = None,
        notes: str | None = None,
        location: str | None = None,
        opened_at: datetime | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "product_id": product_id,
        "barcode": barcode,
        "custom_name": custom_name,
        "category": category,
        "notes": notes,
        "location": location,
        "opened_at": opened_at,
        "amount": amount,
        "unit": unit,
        "expiration_date": expiration_date,
        "status": "active",
        "scheduled_notifications": scheduled_notifications,
        "added_at": now,
        "updated_at": now,
    }
