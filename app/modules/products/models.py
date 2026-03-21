from datetime import datetime, timezone


def build_product_document(
        name: str,
        source: str,
        barcode: str | None = None,
        brand: str | None = None,
        tags: list[str] | None = None,
        image_url: str | None = None,
        quantity: str | None = None
) -> dict:
    """
    Document for MongoDB paste

    :param name: Product name
    :param source: Information source (off - OpenFoodFacts | manual)
    :param barcode: Product barcode
    :param brand: Product brand
    :param tags: Product tags
    :param image_url: Product image url
    :param quantity: Product information (weight, quantity in pack, litres)
    """
    return {
        "barcode": barcode,
        "name": name,
        "brand": brand,
        "tags": tags or [],
        "image_url": image_url,
        "quantity": quantity,
        "source": source,
        "is_verified": source == "off",
        "created_at": datetime.now(timezone.utc)
    }
