from httpx import AsyncClient


MENU_URL = "/api/v1/menu"


MENU_PAYLOAD = {
    "title": "House Pasta",
    "image": "https://example.com/pasta.jpg",
    "ready_in_minutes": 30,
    "servings": 4,
    "calories": 420.5,
    "ingredients": [
        {"id": 11120420, "name": "pasta", "amount": 1, "unit": "pound"},
        {"name": "tomato sauce", "amount": 2, "unit": "cups"},
    ],
    "steps": [
        {"number": 1, "step": "Boil the pasta."},
        {"number": 2, "step": "Mix with sauce."},
    ],
}


async def make_business(headers: dict, client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/auth/account-type",
        json={"account_type": "business"},
        headers=headers,
    )
    assert response.status_code == 200


async def test_business_user_can_create_menu_recipe(client: AsyncClient, auth_headers: dict):
    await make_business(auth_headers, client)

    response = await client.post(MENU_URL, json=MENU_PAYLOAD, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == MENU_PAYLOAD["title"]
    assert data["ingredient_ids"] == [11120420]
    assert data["ingredients"][1]["id"] is None
    assert data["steps"][0]["number"] == 1
    assert "id" in data
    assert "user_id" in data


async def test_personal_user_cannot_create_menu_recipe(client: AsyncClient, auth_headers: dict):
    response = await client.post(MENU_URL, json=MENU_PAYLOAD, headers=auth_headers)

    assert response.status_code == 403


async def test_get_menu_returns_only_current_user_recipes(client: AsyncClient, auth_headers: dict):
    await make_business(auth_headers, client)
    create_response = await client.post(MENU_URL, json=MENU_PAYLOAD, headers=auth_headers)
    assert create_response.status_code == 201

    second_user = {
        "name": "Other User",
        "email": "other@example.com",
        "password": "strongpassword",
    }
    await client.post("/api/v1/auth/register", json=second_user)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": second_user["email"], "password": second_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    await make_business(other_headers, client)
    other_payload = {**MENU_PAYLOAD, "title": "Other Pasta"}
    await client.post(MENU_URL, json=other_payload, headers=other_headers)

    response = await client.get(MENU_URL, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == MENU_PAYLOAD["title"]


async def test_get_menu_requires_auth(client: AsyncClient):
    response = await client.get(MENU_URL)

    assert response.status_code == 401


async def test_create_menu_validates_required_lists(client: AsyncClient, auth_headers: dict):
    await make_business(auth_headers, client)
    payload = {**MENU_PAYLOAD, "ingredients": []}

    response = await client.post(MENU_URL, json=payload, headers=auth_headers)

    assert response.status_code == 422


async def test_create_menu_requires_ingredients_and_steps(client: AsyncClient, auth_headers: dict):
    await make_business(auth_headers, client)
    payload = {
        "title": "Incomplete Pasta",
    }

    response = await client.post(MENU_URL, json=payload, headers=auth_headers)

    assert response.status_code == 422
