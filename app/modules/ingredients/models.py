from datetime import timezone, datetime


def build_normalization_document(
        raw: str,
        normalized: str,
) -> dict:
    """
    Document for ingredient_normalizations collection.

    :param raw: Original product name (e.g. "Milk 3.2%")
    :param normalized: Clean English ingredient name (e.g. "milk")
    """
    return {
        "raw": raw,
        "normalized": normalized,
        "created_at": datetime.now(timezone.utc)
    }