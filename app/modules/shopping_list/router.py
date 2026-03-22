from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependecies import get_current_user
from app.modules.shopping_list.schemas import ShoppingListItemResponse, AddShoppingListItemRequest
from app.modules.shopping_list.service import add_item, get_items, clear_checked, check_item, delete_item

router = APIRouter()


@router.post(
    "",
    response_model=ShoppingListItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to shopping list",
)
async def add_shopping_list_item(
        data: AddShoppingListItemRequest,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await add_item(data, user, db)


@router.get(
    "",
    response_model=list[ShoppingListItemResponse],
    summary="Get shopping list",
)
async def get_shopping_list(
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await get_items(user, db)


@router.delete(
    "/checked",
    summary="Clear all checked items",
)
async def clear_checked_items(
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await clear_checked(user, db)


@router.patch(
    "/{item_id}/check",
    response_model=ShoppingListItemResponse,
    summary="Toggle item checked state",
)
async def check_shopping_list_item(
        item_id: str,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await check_item(item_id, user, db)


@router.delete(
    "/{item_id}",
    summary="Delete shopping list item",
)
async def delete_shopping_list_item(
        item_id: str,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await delete_item(item_id, user, db)
