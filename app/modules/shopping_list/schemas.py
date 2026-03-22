from datetime import datetime
from pydantic import BaseModel, Field
from app.modules.inventory.schemas import UnitEnum


class AddShoppingListItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str | None = None
    amount: float | None = Field(None, gt=0)
    unit: UnitEnum | None = None
    source: str = Field(default="manual", pattern="^(manual|inventory|recipe)$")
    source_id: str | None = None


class ShoppingListItemResponse(BaseModel):
    id: str
    user_id: str
    name: str
    category: str | None = None
    amount: float | None = None
    unit: str | None = None
    is_checked: bool
    source: str
    source_id: str | None = None
    added_at: datetime
