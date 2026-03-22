from itertools import combinations

from motor.motor_asyncio import AsyncIOMotorDatabase
from loguru import logger

from app.modules.ingredients.service import get_normalized
from app.modules.recipes.models import build_recipe_document
from app.modules.recipes.schemas import RecipeResponse
from app.modules.recipes.spoonacular_client import find_recipes_by_ingredients

SPOONACULAR_FETCH_MULTIPLIER = 2


def _extract_all_ingredient_ids(recipe: dict) -> list[int]:
    """Extracts all ingredient ids from a Spoonacular recipe response."""
    ids = []
    for key in ("usedIngredients", "missedIngredients", "unusedIngredients"):
        for ingredient in recipe.get(key, []):
            ing_id = ingredient.get("id")
            if ing_id:
                ids.append(ing_id)
    return list(set(ids))


def _format(doc: dict) -> RecipeResponse:
    return RecipeResponse(
        spoonacular_id=doc["spoonacular_id"],
        title=doc["title"],
        image=doc.get("image"),
    )


async def _fetch_recipes_by_spoonacular_ids(
        spoonacular_ids: list[int],
        db: AsyncIOMotorDatabase,
        number: int,
) -> list[dict]:
    """Fetches recipe documents from DB by their spoonacular_id."""
    cursor = db["recipes"].find(
        {"spoonacular_id": {"$in": spoonacular_ids}},
    ).limit(number)
    return await cursor.to_list(length=number)


async def _search_db_with_combinations(
        recipe_ids_per_ingredient: list[list[int]],
        db: AsyncIOMotorDatabase,
        number: int,
) -> list[dict]:
    """
    Searches DB using progressively smaller subsets of ingredients.

    recipe_ids_per_ingredient: for each ingredient, the list of spoonacular recipe ids
    that were previously fetched when that ingredient was in the query.

    Tries combinations from largest to smallest:
    1. All ingredients together (intersection — most relevant)
    2. All pairs
    3. All singles
    Stops as soon as we reach `number` results.
    Deduplicates by spoonacular_id.
    """
    seen: set[int] = set()
    results: list[dict] = []
    n = len(recipe_ids_per_ingredient)

    for size in range(n, 0, -1):
        if len(results) >= number:
            break

        for combo_indices in combinations(range(n), size):
            if len(results) >= number:
                break

            # For this combination, take the INTERSECTION of recipe_id sets
            # so we get recipes that appeared for ALL selected ingredients
            sets = [set(recipe_ids_per_ingredient[i]) for i in combo_indices]
            if size > 1:
                candidate_ids = list(set.intersection(*sets))
            else:
                candidate_ids = list(sets[0])

            if not candidate_ids:
                continue

            docs = await _fetch_recipes_by_spoonacular_ids(candidate_ids, db, number)
            for doc in docs:
                sid = doc["spoonacular_id"]
                if sid not in seen:
                    results.append(doc)
                    seen.add(sid)

        logger.info(f"DB combinations [{size}/{n} ingredients]: {len(results)} results so far")

    return results[:number]


async def _save_recipes_from_spoonacular(
        spoonacular_results: list[dict],
        db: AsyncIOMotorDatabase,
) -> list[dict]:
    """
    Saves new recipes from Spoonacular to MongoDB.
    Skips recipes that are already cached.
    Returns all recipe documents (new + existing).
    """
    result_docs = []

    for recipe in spoonacular_results:
        spoonacular_id = recipe["id"]

        existing = await db["recipes"].find_one({"spoonacular_id": spoonacular_id})
        if existing:
            result_docs.append(existing)
            continue

        ingredient_ids = _extract_all_ingredient_ids(recipe)
        document = build_recipe_document(
            spoonacular_id=spoonacular_id,
            title=recipe["title"],
            image=recipe.get("image"),
            ingredient_ids=ingredient_ids,
        )
        await db["recipes"].insert_one(document)
        result_docs.append(document)
        logger.info(f"Recipe cached: '{recipe['title']}' (id={spoonacular_id})")

    return result_docs


async def get_recipes_by_ingredients(
        raw_ingredients: list[str],
        tags_map: dict[str, list[str]],
        db: AsyncIOMotorDatabase,
        strategy: str = "soft",
        number: int = 10,
) -> list[RecipeResponse]:
    """
    Main entry point for recipe search.

    Flow:
    1. Normalize each ingredient name via cache → Gemini
    2. For each normalized name find all recipe_ids previously fetched
       for queries containing that ingredient (from recipe_queries collection)
    3. Search DB using combinations of those recipe_id sets (intersection-first)
    4. If not enough → call Spoonacular → cache recipes → store query mapping → merge

    recipe_queries collection schema:
      { query: "eggs,pasta", ingredients: ["eggs", "pasta"], recipe_ids: [649293, ...] }
    """

    # Step 1: Normalize ingredient names
    normalized_names = []
    for raw in raw_ingredients:
        tags = tags_map.get(raw, [])
        normalized = await get_normalized(raw, tags, db)
        if normalized:
            normalized_names.append(normalized)

    if not normalized_names:
        logger.warning("No ingredients could be normalized")
        return []

    # Step 2: For each ingredient, collect all recipe_ids from previous queries
    recipe_ids_per_ingredient: list[list[int]] = []

    for name in normalized_names:
        cursor = db["recipe_queries"].find({"ingredients": name})
        entries = await cursor.to_list(length=100)
        ids: list[int] = []
        for entry in entries:
            ids.extend(entry.get("recipe_ids", []))
        recipe_ids_per_ingredient.append(list(set(ids)))

    # Step 3: Search DB using combinations
    db_results = []
    has_any_ids = any(ids for ids in recipe_ids_per_ingredient)

    if has_any_ids:
        db_results = await _search_db_with_combinations(
            recipe_ids_per_ingredient, db, number=number
        )
        logger.info(f"DB cache returned {len(db_results)} recipes")

    if len(db_results) >= number:
        logger.info("Serving fully from DB cache")
        return [_format(doc) for doc in db_results[:number]]

    # Step 4: Call Spoonacular
    # remaining = number - len(db_results)
    fetch_count = number * SPOONACULAR_FETCH_MULTIPLIER

    logger.info(f"Calling Spoonacular for: {normalized_names}")

    spoonacular_results = await find_recipes_by_ingredients(
        ingredients=normalized_names,
        number=fetch_count,
    )

    if not spoonacular_results:
        logger.warning("Spoonacular returned no results")
        return [_format(doc) for doc in db_results]

    # Step 5: Save recipes and store query → recipe_ids mapping
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

    # Merge and deduplicate
    seen_ids = {doc["spoonacular_id"] for doc in db_results}
    for doc in new_docs:
        if doc["spoonacular_id"] not in seen_ids:
            db_results.append(doc)
            seen_ids.add(doc["spoonacular_id"])

    return [_format(doc) for doc in db_results[:number]]