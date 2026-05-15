from datetime import datetime

from pydantic import BaseModel, Field


class MenuIngredient(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    unit: str = Field(default="", max_length=50)


class MenuStep(BaseModel):
    number: int = Field(..., ge=1)
    step: str = Field(..., min_length=1, max_length=1000)


class CreateMenuRecipeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    image: str | None = Field(None, max_length=500)
    ready_in_minutes: int | None = Field(None, gt=0)
    servings: int | None = Field(None, gt=0)
    calories: float | None = Field(None, ge=0)
    ingredients: list[MenuIngredient] = Field(..., min_length=1)
    steps: list[MenuStep] = Field(..., min_length=1)


class MenuRecipeResponse(BaseModel):
    id: str
    user_id: str
    title: str
    image: str | None = None
    ingredient_ids: list[int] = []
    ready_in_minutes: int | None = None
    servings: int | None = None
    calories: float | None = None
    ingredients: list[MenuIngredient] = []
    steps: list[MenuStep] = []
    created_at: datetime
    updated_at: datetime
