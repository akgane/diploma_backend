from datetime import datetime, timezone

from bson import ObjectId


def build_inventory_document(
        user_id: ObjectId,
        expiration_date: datetime,
        amount: float,
        unit: str,
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
        "added_at": now,
        "updated_at": now,
    }