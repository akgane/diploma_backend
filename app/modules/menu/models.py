from datetime import datetime, timezone

from bson import ObjectId


def build_menu_recipe_document(
        user_id: ObjectId,
        title: str,
        image: str | None = None,
        ready_in_minutes: int | None = None,
        servings: int | None = None,
        calories: float | None = None,
        ingredients: list[dict] | None = None,
        steps: list[dict] | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    ingredients = ingredients or []
    ingredient_ids = [
        ingredient["id"]
        for ingredient in ingredients
        if ingredient.get("id") is not None
    ]

    return {
        "user_id": user_id,
        "title": title,
        "image": image,
        "ingredient_ids": ingredient_ids,
        "ready_in_minutes": ready_in_minutes,
        "servings": servings,
        "calories": calories,
        "ingredients": ingredients,
        "steps": steps or [],
        "created_at": now,
        "updated_at": now,
    }
