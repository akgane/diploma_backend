from pydantic import BaseModel, Field, field_validator

from app.modules.inventory.schemas import UnitEnum


class ManualProductRequest(BaseModel):
    barcode: str | None = Field(None, example="4607034151760")
    name: str = Field(..., min_length=1, max_length=100, example="Milk")
    brand: str | None = Field(None, example="Dairy Everyday")
    tags: list[str] = Field(default=[], example=["dairy", "milk"])
    image_url: str | None = None
    quantity: str | None = Field(None, example="1 l")

    @field_validator("barcode")
    @classmethod
    def barcode_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Barcode cannot be empty or whitespace")
        return v.strip() if v else v


class ProductResponse(BaseModel):
    id: str
    barcode: str | None = None
    name: str
    brand: str | None = None
    tags: list[str] | None = None
    image_url: str | None = None
    quantity: str | None = None
    source: str
    is_verified: bool
