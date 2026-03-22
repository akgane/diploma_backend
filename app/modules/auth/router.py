from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette import status

from app.core.database import get_db
from app.modules.auth.dependecies import get_current_user
from app.modules.auth.schemas import UserResponse, RegisterRequest, TokenResponse, LoginRequest, UpdateFCMTokenRequest, \
    UpdateNotificationSettingsRequest
from app.modules.auth.service import register_user, login_user, update_fcm_token, update_notification_settings

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


@router.patch(
    "/fcm-token",
    summary="Update FCM device token",
)
async def update_fcm_token_endpoint(data: UpdateFCMTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db),
                                    user: dict = Depends(get_current_user)):
    return await update_fcm_token(data.fcm_token, user, db)


@router.patch(
    "/notification-settings",
    summary="Update notification settings",
)
async def update_notification_settings_endpoint(data: UpdateNotificationSettingsRequest,
                                                db: AsyncIOMotorDatabase = Depends(get_db),
                                                user: dict = Depends(get_current_user)):
    return await update_notification_settings(data, user, db)

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        fcm_token=user.get("fcm_token"),
        notification_days_before=user.get("notification_days_before", [3, 1, 0.5]),
        created_at=user["created_at"],
    )