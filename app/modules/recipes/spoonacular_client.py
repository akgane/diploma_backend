import httpx
from loguru import logger

from app.core.config import settings

SPOONACULAR_API_URL = "https://api.spoonacular.com"

async def find_recipes_by_ingredients(
        ingredients: list[str],
        number: int = 10
) -> list[dict] | None:
    """
    Calls Spoonacular API findByIngredients endpoint.
    Returns list of recipes with ingredient details, or None on failure

    Each recipe containes:
    - id, title, image
    - usedIngredients: list of {id, name, ...}
    - missedIngredients: list of {id, name, ...}
    - unusedIngredients: list of {id, name, ...}
    """

    url = f"{SPOONACULAR_API_URL}/recipes/findByIngredients"
    params = {
        "apiKey": settings.SPOONACULAR_API_KEY,
        "ingredients": ",".join(ingredients),
        "number": number,
        "ranking": 1, # maximize used ingredients, 2 to minimize unused ingredients
        "ignorePantry": True
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            logger.info(f"Spoonacular return {len(data)} recipes for: {ingredients}")
            return data
        except Exception as e:
            logger.error(f"Spoonacular request failed: {e}")
            return None


async def get_recipe_information(recipe_id: int) -> dict | None:
    """
    Calls Spoonacular GET /recipes/{id}/information endpoint.
    Returns full recipe details including ingredients, steps, nutrition.
    """
    url = f"{SPOONACULAR_API_URL}/recipes/{recipe_id}/information"
    params = {
        "apiKey": settings.SPOONACULAR_API_KEY,
        "includeNutrition": True,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Spoonacular fetched details for recipe {recipe_id}")
            return data
        except Exception as e:
            logger.error(f"Spoonacular get_recipe_information failed: {e}")
            return None