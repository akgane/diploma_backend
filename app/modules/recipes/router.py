from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.recipes.schemas import RecipeSearchRequest, RecipeResponse, RecipeDetailResponse
from app.modules.recipes.service import get_recipes_by_ingredients, get_recipe_details

router = APIRouter()


@router.post(
    "/by-ingredients",
    response_model=list[RecipeResponse],
    summary="Get recipes by ingredients list",
)
async def search_recipes(
        data: RecipeSearchRequest,
        db: AsyncIOMotorDatabase = Depends(get_db),
        _: dict = Depends(get_current_user),
):
    return await get_recipes_by_ingredients(
        raw_ingredients=data.ingredients,
        tags_map=data.tags_map,
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
