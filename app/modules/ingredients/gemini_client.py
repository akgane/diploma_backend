from google import genai
from google.genai import types
from loguru import logger

from app.core.config import settings

GEMINI_MODEL = "gemini-2.5-flash-lite"

SYSTEM_PROMPT = """You are a food ingredient normalizer.
Your task is to extract the core ingredient name in English from the given product name and tags.
 
Rules:
- Return ONLY one short English ingredient name (1-2 words maximum)
- Remove brand names, percentages, volumes, weights
- Return the most specific ingredient possible
- If the product is a drink, return the drink type (e.g. "milk", "juice", "cola")
- Never return category names like "dairy" or "beverage" if a more specific name is available
- Return lowercase only
 
Examples:
- "Milk 3.2%", tags: ["en:whole-milk"] → milk
- "Coca-Cola Zero 330ml", tags: ["en:sodas"] → cola
- "Wheat bread", tags: ["en:breads", "en:wheat-bread"] → bread
- "Pasta Barilla 500g", tags: ["en:pastas"] → pasta
- "Eggs С1 10", tags: ["en:eggs"] → eggs
 
Respond with ONLY the ingredient name, nothing else."""

async def normalize_ingredient(name: str, tags: list[str]) -> str | None:
    """
    Uses Gemini to normalize a product name to a clean English ingredient name.
    :return: None if normalization failed
    """

    tags_str = ", ".join(tags[:5]) if tags else "none"
    user_message = f'Product: "{name}", tags: [{tags_str}]'

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                max_output_tokens=20
            )
        )

        normalized = response.text.strip().lower()
        logger.info(f"Gemini normalized: '{name}' -> {normalized}")
        return normalized
    except Exception as e:
        logger.error(f"Gemini normalization failed for '{name}': {e}")
        return None