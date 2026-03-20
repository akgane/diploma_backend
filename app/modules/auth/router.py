from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status

from app.core.database import get_db
from app.modules.auth.schemas import UserResponse, RegisterRequest, TokenResponse, LoginRequest
from app.modules.auth.service import register_user, login_user

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="New user registration",
)
async def register(data: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await register_user(data, db)

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and JWT token obtaining"
)
async def login(data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await login_user(data, db)