import re

from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from app.modules.ingredients.gemini_client import normalize_ingredient
from app.modules.ingredients.models import build_normalization_document

_ENGLISH_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\.%]+$')


def _is_english(text: str) -> bool:
    return bool(_ENGLISH_PATTERN.match(text.strip()))


async def get_normalized(
        raw: str,
        tags: list[str],
        db: AsyncIOMotorDatabase,
) -> str | None:
    """
    Returns normalized English ingredient name for a given raw product name.

    Flow:
    1. Check ingredient_normalizations cache in MongoDB
    2. If already English → clean and save directly, skip Gemini
    3. Otherwise → call Gemini → save to cache
    4. Return normalized name or None if all fails
    """

    # 1. Check cache
    cached = await db["ingredient_normalizations"].find_one({"raw": raw})
    if cached:
        logger.info(f"Normalization cache hit: '{raw}' → '{cached['normalized']}'")
        return cached["normalized"]

    # 2. Already English — no need for Gemini
    if _is_english(raw):
        normalized = raw.strip().lower()
        logger.info(f"Already English, skipping Gemini: '{raw}' → '{normalized}'")
        document = build_normalization_document(raw=raw, normalized=normalized)
        await db["ingredient_normalizations"].insert_one(document)
        return normalized

    # 3. Call Gemini
    normalized = await normalize_ingredient(raw, tags)
    if not normalized:
        logger.warning(f"Could not normalize ingredient: '{raw}'")
        return None

    # 4. Save to cache
    document = build_normalization_document(raw=raw, normalized=normalized)
    await db["ingredient_normalizations"].insert_one(document)

    return normalized