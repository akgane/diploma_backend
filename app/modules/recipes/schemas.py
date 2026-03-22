from pydantic import BaseModel, Field


class RecipeSearchRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, example=["Milk 3.2%", "Eggs", "Pasta"])
    tags_map: dict[str, list[str]] = Field(
        default={},
        description="Optional map of ingredient name → OFF tags for better normalization",
        example={"Milk 3.2%": ["en:whole-milk", "en:dairy"]}
    )
    strategy: str = Field(default="soft", pattern="^(soft|strict|percent)$")
    number: int = Field(default=10, ge=1, le=20)


class RecipeResponse(BaseModel):
    spoonacular_id: int
    title: str
    image: str | None = None