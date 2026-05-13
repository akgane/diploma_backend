import json

from google import genai
from google.genai import types
from loguru import logger

from app.core.config import settings

GEMINI_MODEL = "gemini-2.5-flash-lite"

SYSTEM_PROMPT = """You recommend food storage duration.
Return only valid JSON with this shape:
{
  "canonical_name": "short English food name",
  "display_name_en": "English display name",
  "display_name_ru": "Russian display name",
  "category": "fruits|vegetables|meat|fish|dairy|bakery|eggs|prepared_food|grains|beverages|condiments|other",
  "aliases": ["lowercase aliases in English and Russian"],
  "rules": [
    {
      "location": "pantry|fridge|freezer|room",
      "state": "whole|cut|raw|cooked|opened|unopened|fresh",
      "recommended_days": 1,
      "min_days": 1,
      "max_days": 2,
      "is_default": true
    }
  ],
  "confidence": 0.8
}
Use conservative food safety values. If the product is ambiguous, return the safest common case."""


async def fetch_storage_recommendation(
        name: str,
        category: str | None,
        location: str | None,
        state: str | None,
) -> dict | None:
    user_message = json.dumps({
        "name": name,
        "category": category,
        "location": location,
        "state": state,
    }, ensure_ascii=False)

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                max_output_tokens=700,
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini storage recommendation failed for '{name}': {e}")
        return None
