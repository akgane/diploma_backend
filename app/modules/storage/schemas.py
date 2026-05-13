from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class StorageLocationEnum(StrEnum):
    PANTRY = "pantry"
    FRIDGE = "fridge"
    FREEZER = "freezer"
    ROOM = "room"


class StorageStateEnum(StrEnum):
    WHOLE = "whole"
    CUT = "cut"
    RAW = "raw"
    COOKED = "cooked"
    OPENED = "opened"
    UNOPENED = "unopened"
    FRESH = "fresh"


class StorageRule(BaseModel):
    location: StorageLocationEnum
    state: StorageStateEnum
    recommended_days: int = Field(..., gt=0, le=1095)
    min_days: int | None = Field(None, gt=0, le=1095)
    max_days: int | None = Field(None, gt=0, le=1095)
    is_default: bool = False

    @field_validator("max_days")
    @classmethod
    def max_days_not_below_min(cls, v: int | None, info) -> int | None:
        min_days = info.data.get("min_days")
        if v is not None and min_days is not None and v < min_days:
            raise ValueError("max_days cannot be lower than min_days")
        return v


class StorageRecommendationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, example="яблоко")
    category: str | None = Field(None, max_length=50, example="fruits")
    location: StorageLocationEnum | None = Field(None, example="fridge")
    state: StorageStateEnum | None = Field(None, example="whole")


class StorageRecommendationOption(BaseModel):
    location: StorageLocationEnum
    state: StorageStateEnum
    recommended_days: int
    min_days: int | None = None
    max_days: int | None = None


class StorageRecommendationResponse(BaseModel):
    input: str
    canonical_name: str
    display_name: str
    category: str
    recommended_days: int | None = None
    min_days: int | None = None
    max_days: int | None = None
    location: StorageLocationEnum | None = None
    state: StorageStateEnum | None = None
    source: str
    confidence: float = Field(..., ge=0, le=1)
    is_verified: bool
    requires_clarification: bool = False
    options: list[StorageRecommendationOption] = []
