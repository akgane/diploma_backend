from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.recipes.schemas import RecipeSearchRequest, RecipeResponse, RecipeDetailResponse
from app.modules.recipes.service import get_recipes_by_ingredients, get_recipe_details

from loguru import logger

router = APIRouter()


@router.post(
    "/by-ingredients",
    response_model=list[RecipeResponse],
    summary="Get recipes recommendations based on user's current inventory",
)
async def search_recipes(
        data: RecipeSearchRequest,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    # Fetch all active inventory items for the user
    cursor = db["inventory_items"].find({
        "user_id": user["_id"],
        "status": "active",
    })
    items = await cursor.to_list(length=10000)

    # Sort by expiration_date ascending so the soonest-to-expire products are
    # prioritised when the list is capped at MAX_INGREDIENTS in the service.
    now = datetime.now(timezone.utc)

    def _sort_key(item: dict) -> float:
        exp = item.get("expiration_date")
        if exp is None:
            return float("inf")
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = (exp - now).total_seconds()
        # Push already-expired items to the front (negative delta) — still relevant
        return delta

    items.sort(key=_sort_key)

    # Collect unique names in expiry-priority order
    seen: set[str] = set()
    raw_ingredients: list[str] = []
    for item in items:
        name = (item.get("custom_name") or item.get("barcode") or "").strip()
        if name and name not in seen:
            seen.add(name)
            raw_ingredients.append(name)

    if not raw_ingredients:
        return []

    return await get_recipes_by_ingredients(
        raw_ingredients=raw_ingredients,
        db=db,
        strategy=data.strategy,
        number=data.number,
    )


@router.get(
    "/{spoonacular_id}",
    response_model=RecipeDetailResponse,
    summary="Get full recipe details",
)
async def get_recipe(
        spoonacular_id: int,
        db: AsyncIOMotorDatabase = Depends(get_db),
        _: dict = Depends(get_current_user),
):
    return await get_recipe_details(spoonacular_id, db)
