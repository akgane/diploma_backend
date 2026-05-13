from datetime import datetime, timezone

from app.modules.storage.normalization import normalize_storage_name


def build_storage_recommendation_document(
        canonical_name: str,
        display_name: dict[str, str],
        category: str,
        aliases: list[str],
        rules: list[dict],
        source: str,
        is_verified: bool,
        confidence: float,
        requires_clarification: bool = False,
) -> dict:
    normalized_aliases = sorted({
        normalized
        for alias in [canonical_name, *aliases]
        if (normalized := normalize_storage_name(alias))
    })
    now = datetime.now(timezone.utc)
    return {
        "canonical_name": normalize_storage_name(canonical_name),
        "display_name": display_name,
        "category": category,
        "aliases": aliases,
        "normalized_aliases": normalized_aliases,
        "rules": rules,
        "source": source,
        "is_verified": is_verified,
        "confidence": confidence,
        "requires_clarification": requires_clarification,
        "created_at": now,
        "updated_at": now,
    }
