from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.menu.schemas import CreateMenuRecipeRequest, MenuRecipeResponse
from app.modules.menu.service import create_menu_recipe, get_menu_recipes

router = APIRouter()


@router.post(
    "",
    response_model=MenuRecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create menu recipe",
)
async def create_menu_recipe_endpoint(
        data: CreateMenuRecipeRequest,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await create_menu_recipe(data, user, db)


@router.get(
    "",
    response_model=list[MenuRecipeResponse],
    summary="Get current user's menu recipes",
)
async def get_menu_recipes_endpoint(
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await get_menu_recipes(user, db)
