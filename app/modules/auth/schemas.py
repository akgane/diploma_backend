from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, EmailStr

AccountType = Literal["personal", "business"]


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
    notification_days_before: list[Annotated[float, Field(ge=0)]] = Field(
        ...,
        examples=[[3, 1, 0.5]],
        min_length=1
    )


class UpdateAccountTypeRequest(BaseModel):
    account_type: AccountType = Field(..., examples=["personal, business"])


# endregion REQUESTS

# region RESPONSES

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    account_type: AccountType
    fcm_token: str | None = None
    notification_days_before: list[float]
    created_at: datetime


class RegisterResponse(UserResponse):
    access_token: str

# endregion RESPONSES
