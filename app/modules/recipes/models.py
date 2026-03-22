from datetime import datetime, timezone


def build_recipe_document(
        spoonacular_id: int,
        title: str,
        image: str | None,
        ingredient_ids: list[int]
) -> dict:
    """
    Document for recipes collection
    :param spoonacular_id: Spoonacular recipe id
    :param title: Recipe title
    :param image: Recipe image URL
    :param ingredient_ids: List of all Spoonacular ingredient ids used in this recipe
    """
    return {
        "spoonacular_id": spoonacular_id,
        "title": title,
        "image": image,
        "ingredient_ids": ingredient_ids,
        "created_at": datetime.now(timezone.utc),
    }