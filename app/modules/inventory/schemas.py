from datetime import datetime

from pydantic import BaseModel, Field


# region REQUESTS

class AddInventoryItemRequest(BaseModel):
    product_id: str | None = Field(None, example="69be6d9e73b980347699abd2")
    barcode: str | None = Field(None, example="4870055002696")
    custom_name: str | None = Field(None, example="Milk", max_length=100)
    category: str | None = Field(None, example="dairy")
    notes: str | None = Field(None, example="For cereal", max_length=300)
    location: str | None = Field(None, example="Fridge", max_length=100)
    amount: float = Field(..., gt=0, example=1.0)
    unit: str = Field(..., example="l")
    expiration_date: datetime = Field(..., example="2026-04-01T00:00:00")


class UpdateInventoryItemRequest(BaseModel):
    custom_name: str | None = Field(None, max_length=100)
    category: str | None = None
    notes: str | None = Field(None, max_length=300)
    location: str | None = Field(None, max_length=100)
    amount: float | None = Field(None, gt=0)
    unit: str | None = None
    expiration_date: datetime | None = None


class ScheduledNotification(BaseModel):
    threshold: float
    send_at: datetime
    sent: bool


# endregion REQUESTS

# region RESPONSES

class InventoryItemResponse(BaseModel):
    id: str
    user_id: str
    product_id: str | None = None
    barcode: str | None = None
    custom_name: str | None = None
    category: str | None = None
    notes: str | None = None
    location: str | None = None
    opened_at: datetime | None = None
    amount: float
    unit: str
    expiration_date: datetime
    status: str
    added_at: datetime
    updated_at: datetime
    scheduled_notifications: list[ScheduledNotification] = None

# endregion RESPONSES
