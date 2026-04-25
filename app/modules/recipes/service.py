import random
from datetime import date

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from app.modules.ingredients.service import get_normalized
from app.modules.recipes.models import build_recipe_document
from app.modules.recipes.schemas import RecipeResponse
from app.modules.recipes.spoonacular_client import find_recipes_by_ingredients, get_recipe_information

# Maximum number of ingredients sent through the normalization + Spoonacular pipeline.
# Prevents Gemini/Spoonacular quota exhaustion when the user has a large inventory.
# Items are pre-sorted by expiration date (soonest first) in the router so the
# most time-sensitive products are always included.
MAX_INGREDIENTS = 15


# scoring & sorting
def _compute_match_score(user_normalized: set[str], recipe_ingredient_names: list[str]) -> float:
    """
    Computes what percentage of a recipe's ingredients the user already has.
    Uses substring matching: "whole milk" is matched by user ingredient "milk".
    Returns a value in [0.0, 100.0].
    """
    if not recipe_ingredient_names:
        return 0.0

    matched = 0
    for recipe_ing in recipe_ingredient_names:
        for user_ing in user_normalized:
            if user_ing and (user_ing in recipe_ing or recipe_ing in user_ing):
                matched += 1
                break

    return round((matched / len(recipe_ingredient_names)) * 100, 1)


def _sort_with_daily_shuffle(docs: list[dict], user_normalized: set[str]) -> list[dict]:
    """
    1. Computes match_score for every recipe document (stored in "_score").
    2. Sorts DESC by score.
    3. Within groups sharing the same rounded score, applies a deterministic
       daily shuffle so the user sees a fresh order each day without losing
       relevance ordering between groups.
    """
    seed = date.today().toordinal()
    rng = random.Random(seed)

    for doc in docs:
        doc["_score"] = _compute_match_score(user_normalized, doc.get("ingredient_names", []))

    docs.sort(key=lambda d: d["_score"], reverse=True)

    result: list[dict] = []
    i = 0
    while i < len(docs):
        group_score = round(docs[i]["_score"])
        j = i
        while j < len(docs) and round(docs[j]["_score"]) == group_score:
            j += 1
        group = docs[i:j]
        rng.shuffle(group)
        result.extend(group)
        i = j

    return result


# Formatting
def _format(doc: dict) -> RecipeResponse:
    return RecipeResponse(
        spoonacular_id=doc["spoonacular_id"],
        title=doc["title"],
        image=doc.get("image"),
        match_score=doc.get("_score", 0.0),
    )


# Internal DB / Spoonacular helpers
def _extract_all_ingredient_ids(recipe: dict) -> list[int]:
    ids = []
    for key in ("usedIngredients", "missedIngredients", "unusedIngredients"):
        for ingredient in recipe.get(key, []):
            ing_id = ingredient.get("id")
            if ing_id:
                ids.append(ing_id)
    return list(set(ids))


def _extract_ingredient_names(recipe: dict) -> list[str]:
    """
    Extracts lowercase ingredient names (used + missed) from a Spoonacular
    findByIngredients response item, for match-score computation.
    """
    names: set[str] = set()
    for key in ("usedIngredients", "missedIngredients"):
        for ing in recipe.get(key, []):
            name = (ing.get("name") or "").strip().lower()
            if name:
                names.add(name)
    return list(names)


async def _fetch_from_db_by_union(
        normalized_names: list[str],
        db: AsyncIOMotorDatabase,
        number: int,
) -> list[dict]:
    """
    Fetches cached recipes from DB using a simple union strategy:

    1. Find all recipe_queries entries that contain ANY of the normalized names ($in).
    2. Collect the union of all recipe_ids from those entries.
    3. Fetch those recipe documents in a single query.

    This is exactly 2 MongoDB queries regardless of how many ingredients there
    are, replacing the previous O(2^n) combinations approach.
    """
    cursor = db["recipe_queries"].find({"ingredients": {"$in": normalized_names}})
    query_entries = await cursor.to_list(length=1000)

    all_recipe_ids: set[int] = set()
    for entry in query_entries:
        all_recipe_ids.update(entry.get("recipe_ids", []))

    if not all_recipe_ids:
        return []

    # Fetch extra docs so the scorer has headroom to surface the best matches
    cursor = db["recipes"].find({"spoonacular_id": {"$in": list(all_recipe_ids)}})
    docs = await cursor.to_list(length=number * 5)

    logger.info(f"DB union fetch: {len(all_recipe_ids)} candidate ids → {len(docs)} docs")
    return docs


async def _save_recipes_from_spoonacular(
        spoonacular_results: list[dict],
        db: AsyncIOMotorDatabase,
) -> list[dict]:
    result_docs = []

    for recipe in spoonacular_results:
        spoonacular_id = recipe["id"]

        existing = await db["recipes"].find_one({"spoonacular_id": spoonacular_id})
        if existing:
            result_docs.append(existing)
            continue

        ingredient_ids = _extract_all_ingredient_ids(recipe)
        ingredient_names = _extract_ingredient_names(recipe)

        document = build_recipe_document(
            spoonacular_id=spoonacular_id,
            title=recipe["title"],
            image=recipe.get("image"),
            ingredient_ids=ingredient_ids,
            ingredient_names=ingredient_names,
        )
        await db["recipes"].insert_one(document)
        result_docs.append(document)
        logger.info(f"Recipe cached: '{recipe['title']}' (id={spoonacular_id})")

    return result_docs


# Public API
async def get_recipes_by_ingredients(
        raw_ingredients: list[str],
        db: AsyncIOMotorDatabase,
        strategy: str = "soft",
        number: int = 10,
) -> list[RecipeResponse]:
    """
    Main entry point for recipe recommendations.

    Flow:
    1. Cap ingredients at MAX_INGREDIENTS (already sorted by expiry in router)
    2. Normalize each name: DB cache → Gemini; on Gemini failure use raw fallback
    3. Search DB cache via union of all matching recipe_ids (2 queries total)
    4. If not enough → call Spoonacular → cache → update query mapping → merge
    5. Compute match score for every recipe vs user's normalized ingredients
    6. Sort DESC by score; within same-score groups apply daily deterministic shuffle
    """

    # Step 1: Cap
    raw_ingredients = raw_ingredients[:MAX_INGREDIENTS]

    # Step 2: Normalize — fallback to raw lowercase when Gemini is unavailable
    normalized_names: list[str] = []
    for raw in raw_ingredients:
        normalized = await get_normalized(raw, [], db)
        if normalized:
            normalized_names.append(normalized)
        else:
            fallback = raw.strip().lower()
            if fallback:
                normalized_names.append(fallback)
                logger.info(f"Gemini unavailable for '{raw}', using raw fallback: '{fallback}'")

    if not normalized_names:
        logger.warning("No ingredients could be normalized")
        return []

    user_normalized: set[str] = set(normalized_names)

    # Step 3: DB cache — union approach, no combinatorial explosion
    db_results = await _fetch_from_db_by_union(normalized_names, db, number)

    if len(db_results) >= number:
        logger.info("Serving fully from DB cache")
        sorted_docs = _sort_with_daily_shuffle(db_results, user_normalized)
        return [_format(doc) for doc in sorted_docs[:number]]

    # Step 4: Spoonacular
    logger.info(f"Calling Spoonacular for: {normalized_names}")
    spoonacular_results = await find_recipes_by_ingredients(
        ingredients=normalized_names,
        number=number,
    )

    if not spoonacular_results:
        logger.warning("Spoonacular returned no results")
        sorted_docs = _sort_with_daily_shuffle(db_results, user_normalized)
        return [_format(doc) for doc in sorted_docs]

    new_docs = await _save_recipes_from_spoonacular(spoonacular_results, db)
    new_recipe_ids = [doc["spoonacular_id"] for doc in new_docs]

    query_key = ",".join(sorted(normalized_names))
    await db["recipe_queries"].update_one(
        {"query": query_key},
        {"$set": {
            "query": query_key,
            "ingredients": normalized_names,
            "recipe_ids": new_recipe_ids,
        }},
        upsert=True,
    )
    logger.info(f"Query cached: '{query_key}' → {len(new_recipe_ids)} recipes")

    seen_ids = {doc["spoonacular_id"] for doc in db_results}
    for doc in new_docs:
        if doc["spoonacular_id"] not in seen_ids:
            db_results.append(doc)
            seen_ids.add(doc["spoonacular_id"])

    sorted_docs = _sort_with_daily_shuffle(db_results, user_normalized)
    return [_format(doc) for doc in sorted_docs[:number]]


# Recipe detail
def _parse_recipe_details(data: dict) -> dict:
    calories = None
    for nutrient in data.get("nutrition", {}).get("nutrients", []):
        if nutrient.get("name") == "Calories":
            calories = nutrient.get("amount")
            break

    ingredients = [
        {
            "id": ing.get("id"),
            "name": ing.get("nameClean") or ing.get("name", ""),
            "amount": ing.get("amount", 0),
            "unit": ing.get("unit", ""),
        }
        for ing in data.get("extendedIngredients", [])
    ]

    steps = []
    analyzed = data.get("analyzedInstructions", [])
    if analyzed:
        for step in analyzed[0].get("steps", []):
            steps.append({"number": step.get("number"), "step": step.get("step", "")})

    return {
        "details_fetched": True,
        "ready_in_minutes": data.get("readyInMinutes"),
        "servings": data.get("servings"),
        "calories": calories,
        "ingredients": ingredients,
        "steps": steps,
    }


async def get_recipe_details(spoonacular_id: int, db: AsyncIOMotorDatabase) -> dict:
    doc = await db["recipes"].find_one({"spoonacular_id": spoonacular_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe {spoonacular_id} not found",
        )

    if doc.get("details_fetched"):
        logger.info(f"Recipe {spoonacular_id} details served from cache")
        return doc

    data = await get_recipe_information(spoonacular_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch recipe details from Spoonacular",
        )

    details = _parse_recipe_details(data)
    await db["recipes"].update_one(
        {"spoonacular_id": spoonacular_id},
        {"$set": details},
    )

    doc.update(details)
    logger.info(f"Recipe {spoonacular_id} details cached")
    return doc