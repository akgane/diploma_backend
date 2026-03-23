from datetime import datetime, timezone

from fastapi import HTTPException, status

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password, verify_password, create_access_token
from app.modules.auth.models import build_user_document
from app.modules.auth.schemas import RegisterRequest, UserResponse, TokenResponse, LoginRequest, \
    UpdateNotificationSettingsRequest

from loguru import logger


async def register_user(data: RegisterRequest, db: AsyncIOMotorDatabase) -> UserResponse:
    """
    Registers new user
    """

    existing = await db["users"].find_one({"email": data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    hashed = hash_password(data.password)
    document = build_user_document(
        name=data.name,
        email=data.email,
        hashed_password=hashed,
    )

    result = await db["users"].insert_one(document)

    login_request = LoginRequest(
        email=data.email,
        password=data.password
    )
    access_token = (await login_user(login_request, db)).access_token

    return UserResponse(
        id=str(result.inserted_id),
        name=document["name"],
        email=document["email"],
        notification_days_before=document["notification_days_before"],
        access_token=access_token,
        created_at=document["created_at"],
    )


async def login_user(data: LoginRequest, db: AsyncIOMotorDatabase) -> TokenResponse:
    """Checks credentials and return JWT token"""

    user = await db["users"].find_one({"email": data.email})

    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user["_id"]))
    return TokenResponse(access_token=token)


async def update_fcm_token(token: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {"fcm_token": token, "updated_at": datetime.now(timezone.utc)}}
    )

    logger.info(f"FCM token updated for user {user['_id']}")
    return {"detail": "FCM token updated"}


async def update_notification_settings(data: UpdateNotificationSettingsRequest, user: dict,
                                       db: AsyncIOMotorDatabase) -> dict:
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "notification_days_before": data.notification_days_before,
            "updated_at": datetime.now(timezone.utc),
        }}
    )
    logger.info(f"Notification settings updated for user {user["_id"]}")
    return {"detail": "Notification settings updated"}
