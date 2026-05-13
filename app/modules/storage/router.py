from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.storage.schemas import StorageRecommendationRequest, StorageRecommendationResponse
from app.modules.storage.service import recommend_storage

router = APIRouter()


@router.post(
    "/recommendations",
    response_model=StorageRecommendationResponse,
    summary="Recommend product storage duration",
)
async def get_storage_recommendation(
        data: StorageRecommendationRequest,
        db: AsyncIOMotorDatabase = Depends(get_db),
        _: dict = Depends(get_current_user),
):
    return await recommend_storage(data, db)
