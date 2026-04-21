from fastapi import APIRouter, Depends, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.products.schemas import ProductResponse, ManualProductRequest
from app.modules.products.service import get_or_fetch, create_manual

router = APIRouter()

@router.get(
    "/{barcode}",
    response_model=ProductResponse,
    summary="Search product by barcode (DB -> OpenFoodFacts)",
)
async def search_by_barcode(
        barcode: str = Path(..., min_length=1, max_length=50, pattern=r"^\S+$"),
        db: AsyncIOMotorDatabase = Depends(get_db),
        _: dict = Depends(get_current_user)
):
    return await get_or_fetch(barcode, db)

@router.post(
    "/create",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create new product",
)
async def create_product(
        data: ManualProductRequest, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(get_current_user)
):
    return await create_manual(data, db)