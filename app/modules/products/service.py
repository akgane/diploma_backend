from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.products.models import build_product_document
from app.modules.products.off_client import fetch_product_by_barcode
from app.modules.products.schemas import ProductResponse, ManualProductRequest

from loguru import logger

from app.modules.products.utils import format_fields


def _format(doc: dict) -> ProductResponse:
    return ProductResponse(
        id=str(doc["_id"]),
        barcode=doc.get("barcode"),
        name=doc.get("name"),
        brand=doc.get("brand"),
        tags=doc.get("tags", []),
        image_url=doc.get("image_url"),
        quantity=doc.get("quantity"),
        source=doc.get("source"),
        is_verified=doc.get("is_verified"),
    )

async def get_or_fetch(barcode: str, db: AsyncIOMotorDatabase) -> ProductResponse:
    """
    1. Searches product in database
    2. Fetches OpenFoodFacts
    3. Return None
    :return: ProductResponse or None
    """

    # Fetching db
    existing = await db["products"].find_one({"barcode": barcode})
    if existing:
        logger.info(f"Product found in DB: {barcode}")
        return _format(existing)

    off_data = await fetch_product_by_barcode(barcode)
    if off_data and off_data.get("name"):
        # formatting fields before paste to db
        off_data = format_fields(off_data)

        # building document
        document = build_product_document(**off_data)

        # inserting to db
        result = await db["products"].insert_one(document)
        document["_id"] = result.inserted_id
        logger.info(f"Product fetched from OpenFoodFacts: {barcode}")
        return _format(document)

    logger.warning(f"Product not found anywhere: {barcode}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product not found. Try adding it manually"
    )

async def create_manual(
        data: ManualProductRequest, db: AsyncIOMotorDatabase
) -> ProductResponse:
    """
    Manual product information add
    """
    if data.barcode:
        existing = await db["products"].find_one({"barcode": data.barcode})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this barcode already exists",
            )

    document = build_product_document(
        barcode=data.barcode,
        name=data.name,
        brand=data.brand,
        tags=data.tags,
        image_url=data.image_url,
        quantity=data.quantity,
        source="manual",
    )

    result = await db["products"].insert_one(document)
    document["_id"] = result.inserted_id
    return _format(document)