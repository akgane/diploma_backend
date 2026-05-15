from fastapi import HTTPException, status
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.menu.models import build_menu_recipe_document
from app.modules.menu.schemas import CreateMenuRecipeRequest, MenuRecipeResponse


def _ensure_business_user(user: dict) -> None:
    if user.get("account_type", "personal") != "business":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only business users can create menu recipes",
        )


def _format(doc: dict) -> MenuRecipeResponse:
    return MenuRecipeResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        title=doc["title"],
        image=doc.get("image"),
        ingredient_ids=doc.get("ingredient_ids", []),
        ready_in_minutes=doc.get("ready_in_minutes"),
        servings=doc.get("servings"),
        calories=doc.get("calories"),
        ingredients=doc.get("ingredients", []),
        steps=doc.get("steps", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_menu_recipe(
        data: CreateMenuRecipeRequest,
        user: dict,
        db: AsyncIOMotorDatabase,
) -> MenuRecipeResponse:
    _ensure_business_user(user)

    document = build_menu_recipe_document(
        user_id=user["_id"],
        title=data.title,
        image=data.image,
        ready_in_minutes=data.ready_in_minutes,
        servings=data.servings,
        calories=data.calories,
        ingredients=[
            ingredient.model_dump()
            for ingredient in data.ingredients
        ],
        steps=[
            step.model_dump()
            for step in data.steps
        ],
    )

    result = await db["menu_recipes"].insert_one(document)
    document["_id"] = result.inserted_id

    logger.info(f"Menu recipe created for user {user['_id']}: {data.title}")
    return _format(document)


async def get_menu_recipes(
        user: dict,
        db: AsyncIOMotorDatabase,
) -> list[MenuRecipeResponse]:
    cursor = db["menu_recipes"].find(
        {"user_id": user["_id"]}
    ).sort("created_at", -1)
    recipes = await cursor.to_list(length=10000)
    return [_format(doc) for doc in recipes]
