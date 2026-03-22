import httpx

API_URL = "https://world.openfoodfacts.net/api/v2"
OFF_USER_AGENT="FoodTrackerDiploma/1.0"

OFF_FETCH_COUNTRY = "kz"
OFF_FETCH_LANGUAGE = "en"

def _clean_tags(raw_tags: list[str]) -> list[str]:
    """
    Cleans tags from OpenFoodFacts API
    'en:cola' -> 'cola'
    """
    cleaned = []
    for tag in raw_tags:
        value = tag.split(":", 1)[-1]
        if value:
            cleaned.append(value)
    return cleaned

async def fetch_product_by_barcode(barcode: str) -> dict | None:
    url = f"{API_URL}/product/{barcode}"
    fields = "product_name,brands,categories_tags,image_url,quantity"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, params={"fields": fields, "cc": OFF_FETCH_COUNTRY, "lc": OFF_FETCH_LANGUAGE})
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None

    if data.get("status") != 1:
        return None

    product = data.get("product", {})

    return {
        "barcode": barcode,
        "name": product.get("product_name") or None,
        "brand": product.get("brands") or None,
        "tags": _clean_tags(product.get("categories_tags", [])),
        "image_url": product.get("image_url") or None,
        "quantity": product.get("quantity") or None,
        "source": "off"
    }
