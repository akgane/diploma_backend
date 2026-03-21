from datetime import timezone, datetime, timedelta

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.inventory.models import build_inventory_document, build_scheduled_notifications
from app.modules.inventory.schemas import InventoryItemResponse, AddInventoryItemRequest, UpdateInventoryItemRequest

from loguru import logger


def _format(doc: dict) -> InventoryItemResponse:
    return InventoryItemResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        product_id=str(doc["product_id"]) if doc.get("product_id") else None,
        barcode=doc.get("barcode"),
        custom_name=doc.get("custom_name"),
        category=doc.get("category"),
        notes=doc.get("notes"),
        location=doc.get("location"),
        opened_at=doc.get("opened_at"),
        amount=doc["amount"],
        unit=doc["unit"],
        expiration_date=doc["expiration_date"],
        status=doc["status"],
        added_at=doc["added_at"],
        updated_at=doc["updated_at"],
    )


async def add_item(data: AddInventoryItemRequest, user: dict, db: AsyncIOMotorDatabase) -> InventoryItemResponse:
    """
    Adding product to user's inventory
    :param data: Product data
    :param user: User
    :return:
    """
    product_id = ObjectId(data.product_id) if data.product_id else None

    if data.expiration_date.tzinfo is None:
        expiration_date = data.expiration_date.replace(tzinfo=timezone.utc)
    else:
        expiration_date = data.expiration_date

    thresholds = user.get("notification_days_before", [3, 1, 0.5])
    scheduled = build_scheduled_notifications(expiration_date, thresholds)

    document = build_inventory_document(
        user_id=user["_id"],
        product_id=product_id,
        barcode=data.barcode,
        custom_name=data.custom_name,
        category=data.category,
        notes=data.notes,
        location=data.location,
        amount=data.amount,
        unit=data.unit,
        expiration_date=expiration_date,
        scheduled_notifications=scheduled,
    )

    result = await db["inventory_items"].insert_one(document)
    document["_id"] = result.inserted_id
    logger.info(f"Inventory item added for user {user['_id']}")
    return _format(document)


async def get_items(user: dict, db: AsyncIOMotorDatabase, status_filter: str | None = None) -> list[
    InventoryItemResponse]:
    """
    Get all inventory items for user
    :param user: User
    :param status_filter: Filter by status
    """
    query = {"user_id": user["_id"], "status": {"$ne": "deleted"}}
    if status_filter:
        query["status"] = status_filter

    cursor = db["inventory_items"].find(query).sort("expiration_date", 1)
    items = await cursor.to_list()

    return [_format(doc) for doc in items]


async def get_item(item_id: str, user: dict, db: AsyncIOMotorDatabase) -> InventoryItemResponse:
    """
    Get inventory item by id
    """
    doc = await db["inventory_items"].find_one({
        "_id": ObjectId(item_id),
        "user_id": user["_id"],
    })
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Item with id {item_id} not found for user {user['_id']}")
    return _format(doc)


async def update_item(item_id: str, data: UpdateInventoryItemRequest, user: dict,
                      db: AsyncIOMotorDatabase) -> InventoryItemResponse:
    """
    Update inventory item by id
    """
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Nothing to update")

    if "expiration_date" in updates:
        exp = updates["expiration_date"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
            updates["expiration_date"] = exp

        thresholds = user.get("notification_days_before", [3, 1, 0.5])
        updates["scheduled_notifications"] = build_scheduled_notifications(exp, thresholds)

    updates["updated_at"] = datetime.now(timezone.utc)

    result = await db["inventory_items"].find_one_and_update(
        {"_id": ObjectId(item_id), "user_id": user["_id"]},
        {"$set": updates},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Item with id {item_id} not found for user {user['_id']}")

    return _format(result)


async def consume_item(item_id: str, user: dict, db: AsyncIOMotorDatabase) -> InventoryItemResponse:
    """
    Consume item by id
    """
    result = await db["inventory_items"].find_one_and_update(
        {"_id": ObjectId(item_id), "user_id": user["_id"]},
        {"$set": {"status": "consumed", "updated_at": datetime.now(timezone.utc)}},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Item with id {item_id} not found for user {user['_id']}")

    return _format(result)


async def delete_item(item_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    """
    Soft delete item by id
    """
    result = await db["inventory_items"].find_one_and_update(
        {"_id": ObjectId(item_id), "user_id": user["_id"]},
        {"$set": {"status": "deleted", "updated_at": datetime.now(timezone.utc)}},
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Item with id {item_id} not found for user {user['_id']}")

    return {"detail": "Item deleted"}


async def get_expiring_items(user: dict, db: AsyncIOMotorDatabase, days: int = 3) -> list[InventoryItemResponse]:
    """
    Get all expiring items for user
    :param days: days before expiring
    """
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=days)

    cursor = db["inventory_items"].find({
        "user_id": user["_id"],
        "status": "active",
        "expiration_date": {"$gte": now, "$lte": threshold},
    }).sort("expiration_date", 1)

    items = await cursor.to_list()

    return [_format(doc) for doc in items]
