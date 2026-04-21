from bson import ObjectId
from fastapi import HTTPException, status
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.shopping_list.models import build_shopping_list_item_document
from app.modules.shopping_list.schemas import ShoppingListItemResponse, AddShoppingListItemRequest


def _format(doc: dict) -> ShoppingListItemResponse:
    return ShoppingListItemResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        name=doc["name"],
        category=doc.get("category"),
        amount=doc.get("amount"),
        unit=doc.get("unit"),
        is_checked=doc["is_checked"],
        source=doc["source"],
        source_id=doc.get("source_id"),
        added_at=doc.get("added_at"),
    )


async def add_item(
        data: AddShoppingListItemRequest,
        user: dict,
        db: AsyncIOMotorDatabase
) -> ShoppingListItemResponse:
    document = build_shopping_list_item_document(
        user_id=user["_id"],
        name=data.name,
        category=data.category,
        amount=data.amount,
        unit=data.unit,
        source=data.source,
        source_id=data.source_id,
    )
    result = await db["shopping_list_items"].insert_one(document)
    document["_id"] = result.inserted_id
    logger.info(f"Shopping list item added for user {user['_id']}")
    return _format(document)


async def get_items(
        user: dict,
        db: AsyncIOMotorDatabase
) -> list[ShoppingListItemResponse]:
    cursor = db["shopping_list_items"].find(
        {"user_id": user["_id"]}
    ).sort("added_at", 1)
    items = await cursor.to_list(length=10000)
    return [_format(doc) for doc in items]


async def check_item(
        item_id: str,
        user: dict,
        db: AsyncIOMotorDatabase
) -> ShoppingListItemResponse:
    doc = await db["shopping_list_items"].find_one_and_update(
        {"_id": ObjectId(item_id), "user_id": user["_id"]},
        [{"$set": {"is_checked": {"$not": "$is_checked"}}}],  # toggle
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item with id {item_id} not found")
    return _format(doc)


async def delete_item(
        item_id: str,
        user: dict,
        db: AsyncIOMotorDatabase,
) -> dict:
    result = await db["shopping_list_items"].find_one_and_delete(
        {"_id": ObjectId(item_id), "user_id": user["_id"]}
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item with id {item_id} not found")
    return {"detail": "Item deleted"}


async def clear_checked(
        user: dict,
        db: AsyncIOMotorDatabase,
) -> dict:
    result = await db["shopping_list_items"].delete_many(
        {"user_id": user["_id"], "is_checked": True}
    )
    logger.info(f"Cleared {result.deleted_count} checked items for user {user['_id']}")
    return {"detail": f"Deleted {result.deleted_count} items"}
