def format_fields(product: dict) -> dict:
    """
    Formats different fields of fetched product from OpenFoodFacts
    Example: 'coca-Cola zero' -> 'Coca-Cola Zero'
    """
    if product and product.get("name"):
        product["name"] = product["name"].title()

    return product