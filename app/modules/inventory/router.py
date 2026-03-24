from fastapi import APIRouter, status, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependecies import get_current_user
from app.modules.inventory.constants import RECOMMENDED_CATEGORIES
from app.modules.inventory.schemas import InventoryItemResponse, AddInventoryItemRequest, UpdateInventoryItemRequest, \
    UnitEnum, InventoryStatsResponse
from app.modules.inventory.service import add_item, get_items, get_expiring_items, get_item, update_item, consume_item, \
    delete_item, get_stats

router = APIRouter()


# region meta

@router.get(
    "/meta/units",
    summary="Get available units",
)
async def get_units():
    return list(UnitEnum)


@router.get(
    "/meta/categories",
    summary="Get recommended categories",
)
async def get_categories():
    return RECOMMENDED_CATEGORIES


# endregion meta


# region inventory

@router.post(
    "/add",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to inventory",
)
async def add_inventory_item(data: AddInventoryItemRequest, db: AsyncIOMotorDatabase = Depends(get_db),
                             user: dict = Depends(get_current_user)):
    return await add_item(data, user, db)


@router.get(
    "",
    response_model=list[InventoryItemResponse],
    summary="Get current user inventory",
)
async def get_inventory(status_filter: str | None = Query(None, alias="status"),
                        db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(get_current_user)):
    return await get_items(user, db, status_filter)


@router.get(
    "/expiring",
    response_model=list[InventoryItemResponse],
    summary="Get expiring items in N days",
)
async def get_expiring(days: int = Query(3, ge=1, le=30), db: AsyncIOMotorDatabase = Depends(get_db),
                       user: dict = Depends(get_current_user)):
    return await get_expiring_items(user, db, days)


@router.get(
    "/stats",
    response_model=InventoryStatsResponse,
    summary="Get inventory statistics"
)
async def get_inventory_stats(db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(get_current_user)):
    return await get_stats(user, db)


@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Get item from inventory by id",
)
async def get_inventory_item(item_id: str, db: AsyncIOMotorDatabase = Depends(get_db),
                             user: dict = Depends(get_current_user)):
    return await get_item(item_id, user, db)


@router.patch(
    "/{item_id}/consume",
    response_model=InventoryItemResponse,
    summary="Mark item as consumed",
)
async def consume_inventory_item(
        item_id: str,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await consume_item(item_id, user, db)


@router.patch(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Update inventory item"
)
async def update_inventory_item(item_id: str, data: UpdateInventoryItemRequest,
                                db: AsyncIOMotorDatabase = Depends(get_db), user: dict = Depends(get_current_user)):
    return await update_item(item_id, data, user, db)


@router.delete(
    "/{item_id}",
    summary="Soft delete inventory item",
)
async def delete_inventory_item(
        item_id: str,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(get_current_user),
):
    return await delete_item(item_id, user, db)

# endregion inventory
