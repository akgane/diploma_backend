from datetime import datetime, timezone

from fastapi import HTTPException, status
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError

from app.modules.storage.constants import CATEGORIES
from app.modules.storage.gemini_client import fetch_storage_recommendation
from app.modules.storage.models import build_storage_recommendation_document
from app.modules.storage.normalization import normalize_storage_name
from app.modules.storage.schemas import (
    StorageRecommendationOption,
    StorageRecommendationRequest,
    StorageRecommendationResponse,
    StorageRule,
)


def _display_name(doc: dict) -> str:
    display_name = doc.get("display_name") or {}
    return display_name.get("ru") or display_name.get("en") or doc["canonical_name"].title()


def _rule_options(rules: list[dict]) -> list[StorageRecommendationOption]:
    options = []
    for rule in rules:
        try:
            validated = StorageRule.model_validate(rule)
            options.append(StorageRecommendationOption(
                location=validated.location,
                state=validated.state,
                recommended_days=validated.recommended_days,
                min_days=validated.min_days,
                max_days=validated.max_days,
            ))
        except ValidationError:
            continue
    return options


def _select_rule(doc: dict, data: StorageRecommendationRequest) -> StorageRule | None:
    rules = []
    for rule in doc.get("rules", []):
        try:
            rules.append(StorageRule.model_validate(rule))
        except ValidationError:
            continue

    if not rules:
        return None

    if data.location and data.state:
        for rule in rules:
            if rule.location == data.location and rule.state == data.state:
                return rule

    if data.location:
        for rule in rules:
            if rule.location == data.location and rule.is_default:
                return rule
        for rule in rules:
            if rule.location == data.location:
                return rule

    if data.state:
        for rule in rules:
            if rule.state == data.state and rule.is_default:
                return rule
        for rule in rules:
            if rule.state == data.state:
                return rule

    for rule in rules:
        if rule.is_default:
            return rule

    return rules[0]


def _format_response(
        input_name: str,
        doc: dict,
        data: StorageRecommendationRequest,
) -> StorageRecommendationResponse:
    rule = _select_rule(doc, data)
    options = _rule_options(doc.get("rules", []))
    requires_clarification = bool(doc.get("requires_clarification")) and not data.location and not data.state

    return StorageRecommendationResponse(
        input=input_name,
        canonical_name=doc["canonical_name"],
        display_name=_display_name(doc),
        category=doc.get("category", "other"),
        recommended_days=rule.recommended_days if rule and not requires_clarification else None,
        min_days=rule.min_days if rule and not requires_clarification else None,
        max_days=rule.max_days if rule and not requires_clarification else None,
        location=rule.location if rule and not requires_clarification else None,
        state=rule.state if rule and not requires_clarification else None,
        source=doc.get("source", "database"),
        confidence=doc.get("confidence", 1.0),
        is_verified=doc.get("is_verified", False),
        requires_clarification=requires_clarification,
        options=options,
    )


def _seed_document(seed: dict) -> dict:
    return build_storage_recommendation_document(
        canonical_name=seed["canonical_name"],
        display_name=seed["display_name"],
        category=seed["category"],
        aliases=seed["aliases"],
        rules=seed["rules"],
        source="database",
        is_verified=True,
        confidence=1.0,
        requires_clarification=seed.get("requires_clarification", False),
    )


def _find_seed(normalized_name: str) -> dict | None:
    for seed in DEFAULT_STORAGE_RECOMMENDATIONS:
        aliases = [seed["canonical_name"], *seed["aliases"]]
        if normalized_name in {normalize_storage_name(alias) for alias in aliases}:
            return _seed_document(seed)
    return None


async def _find_cached(normalized_name: str, db: AsyncIOMotorDatabase) -> dict | None:
    return await db["storage_recommendations"].find_one({
        "$or": [
            {"canonical_name": normalized_name},
            {"normalized_aliases": normalized_name},
        ]
    })


async def _cache_document(document: dict, db: AsyncIOMotorDatabase) -> dict:
    document["updated_at"] = datetime.now(timezone.utc)
    await db["storage_recommendations"].update_one(
        {"canonical_name": document["canonical_name"]},
        {"$setOnInsert": document},
        upsert=True,
    )
    return await db["storage_recommendations"].find_one({"canonical_name": document["canonical_name"]}) or document


def _validated_category(value: str | None) -> str:
    if value in CATEGORIES:
        return value
    return "other"


def _build_ai_document(data: StorageRecommendationRequest, normalized_name: str, ai_data: dict) -> dict | None:
    canonical_name = normalize_storage_name(str(ai_data.get("canonical_name") or normalized_name))
    if not canonical_name:
        return None

    category = _validated_category(ai_data.get("category") or data.category)
    aliases = ai_data.get("aliases") if isinstance(ai_data.get("aliases"), list) else []
    aliases = [str(alias) for alias in aliases if str(alias).strip()]
    aliases.extend([data.name, normalized_name, canonical_name])

    raw_rules = ai_data.get("rules") if isinstance(ai_data.get("rules"), list) else []
    rules = []
    for raw_rule in raw_rules:
        try:
            rules.append(StorageRule.model_validate(raw_rule).model_dump(mode="json"))
        except ValidationError:
            continue

    if not rules:
        return None

    if not any(rule.get("is_default") for rule in rules):
        rules[0]["is_default"] = True

    confidence = ai_data.get("confidence", 0.6)
    try:
        confidence = max(0, min(float(confidence), 1))
    except (TypeError, ValueError):
        confidence = 0.6

    display_name_en = str(ai_data.get("display_name_en") or canonical_name.title())
    display_name_ru = str(ai_data.get("display_name_ru") or display_name_en)

    return build_storage_recommendation_document(
        canonical_name=canonical_name,
        display_name={"en": display_name_en, "ru": display_name_ru},
        category=category,
        aliases=aliases,
        rules=rules,
        source="gemini",
        is_verified=False,
        confidence=confidence,
    )


async def recommend_storage(
        data: StorageRecommendationRequest,
        db: AsyncIOMotorDatabase,
) -> StorageRecommendationResponse:
    input_name = data.name.strip()
    normalized_name = normalize_storage_name(input_name)
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product name is invalid")

    cached = await _find_cached(normalized_name, db)
    if cached:
        logger.info(f"Storage recommendation cache hit: '{input_name}'")
        return _format_response(input_name, cached, data)

    # seed = _find_seed(normalized_name)
    # if seed:
    #     cached_seed = await _cache_document(seed, db)
    #     logger.info(f"Storage recommendation seeded: '{input_name}'")
    #     return _format_response(input_name, cached_seed, data)

    ai_data = await fetch_storage_recommendation(
        name=input_name,
        category=data.category,
        location=data.location,
        state=data.state,
    )
    if not ai_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage recommendation not found",
        )

    document = _build_ai_document(data, normalized_name, ai_data)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage recommendation not found",
        )

    cached_ai = await _cache_document(document, db)
    logger.info(f"Storage recommendation cached from Gemini: '{input_name}'")
    return _format_response(input_name, cached_ai, data)
