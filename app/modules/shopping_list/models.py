from datetime import timezone, datetime


def build_shopping_list_item_document(
        user_id: str,
        name: str,
        category: str | None = None,
        amount: float | None = None,
        unit: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "name": name,
        "category": category,
        "amount": amount,
        "unit": unit,
        "is_checked": False,
        "source": source,
        "source_id": source_id,
        "added_at": now,
    }
