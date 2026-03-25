import html


def format_fields(product: dict) -> dict:
    """
    Formats different fields of fetched product from OpenFoodFacts
    Example: 'coca-Cola zero' -> 'Coca-Cola Zero'
    Example: '&quot;Slavyanka&quot;' -> '"Slavyanka"'
    """
    if product and product.get("name"):
        product["name"] = html.unescape(product["name"]).title()

    return product