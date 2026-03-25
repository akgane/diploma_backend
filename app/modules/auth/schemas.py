from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


# region REQUESTS

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, example="John")
    email: EmailStr = Field(..., example="john@doe.com")
    password: str = Field(..., min_length=6, max_length=100, example="strongpassword")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="john@doe.com")
    password: str = Field(..., example="strongpassword")


class UpdateFCMTokenRequest(BaseModel):
    fcm_token: str = Field(..., example="eF3k2...")


class UpdateNotificationSettingsRequest(BaseModel):
    notification_days_before: list[float] = Field(..., example=[3, 1, 0.5], min_length=1)


# endregion REQUESTS

# region RESPONSES

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    fcm_token: str | None = None
    notification_days_before: list[float]
    created_at: datetime


class RegisterResponse(UserResponse):
    access_token: str

# endregion RESPONSES
