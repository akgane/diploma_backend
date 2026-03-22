from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

PRODUCTS_URL = "/api/v1/products"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

VALID_USER = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "strongpassword",
}

MANUAL_PRODUCT = {
    "name": "Milk",
    "brand": "DairyFarm",
    "barcode": "1234567890",
    "tags": ["dairy", "milk"],
    "quantity": "1 l",
}

OFF_MOCK_RESPONSE = {
    "barcode": "5449000000996",
    "name": "Coca-Cola",
    "brand": "Coca-Cola",
    "tags": ["beverages", "soda"],
    "image_url": "http://example.com/cocacola.jpg",
    "quantity": "330 ml",
    "source": "off",
}


async def get_auth_headers(client: AsyncClient) -> dict:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSearchByBarcode:
    async def test_found_in_db(self, client: AsyncClient):
        """Product is returned from DB without calling OFF"""
        headers = await get_auth_headers(client)

        # First create product manually so it exists in DB
        await client.post(f"{PRODUCTS_URL}/create", json=MANUAL_PRODUCT, headers=headers)

        with patch("app.modules.products.service.fetch_product_by_barcode") as mock_off:
            response = await client.get(f"{PRODUCTS_URL}/{MANUAL_PRODUCT['barcode']}", headers=headers)
            mock_off.assert_not_called()

        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == MANUAL_PRODUCT["barcode"]
        assert data["name"] == MANUAL_PRODUCT["name"].title()

    async def test_fetched_from_off(self, client: AsyncClient):
        """Product not in DB — fetched from OpenFoodFacts and saved"""
        headers = await get_auth_headers(client)

        with patch(
            "app.modules.products.service.fetch_product_by_barcode",
            new_callable=AsyncMock,
            return_value=OFF_MOCK_RESPONSE,
        ):
            response = await client.get(f"{PRODUCTS_URL}/5449000000996", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Coca-Cola"
        assert data["source"] == "off"
        assert data["is_verified"] is True

    async def test_off_returns_none_raises_404(self, client: AsyncClient):
        """Product not found anywhere — 404"""
        headers = await get_auth_headers(client)

        with patch(
            "app.modules.products.service.fetch_product_by_barcode",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get(f"{PRODUCTS_URL}/0000000000000", headers=headers)

        assert response.status_code == 404

    async def test_off_returns_no_name_raises_404(self, client: AsyncClient):
        """OFF returns data but without name — treated as not found"""
        headers = await get_auth_headers(client)

        with patch(
            "app.modules.products.service.fetch_product_by_barcode",
            new_callable=AsyncMock,
            return_value={"barcode": "0000000000000", "name": None},
        ):
            response = await client.get(f"{PRODUCTS_URL}/0000000000000", headers=headers)

        assert response.status_code == 404

    async def test_second_call_uses_db_cache(self, client: AsyncClient):
        """Second request for same barcode uses DB, not OFF"""
        headers = await get_auth_headers(client)

        with patch(
            "app.modules.products.service.fetch_product_by_barcode",
            new_callable=AsyncMock,
            return_value=OFF_MOCK_RESPONSE,
        ) as mock_off:
            await client.get(f"{PRODUCTS_URL}/5449000000996", headers=headers)
            await client.get(f"{PRODUCTS_URL}/5449000000996", headers=headers)
            assert mock_off.call_count == 1

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.get(f"{PRODUCTS_URL}/1234567890")
        assert response.status_code == 401


class TestCreateManualProduct:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{PRODUCTS_URL}/create", json=MANUAL_PRODUCT, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == MANUAL_PRODUCT["name"].title()
        assert data["brand"] == MANUAL_PRODUCT["brand"]
        assert data["barcode"] == MANUAL_PRODUCT["barcode"]
        assert data["source"] == "manual"
        assert data["is_verified"] is False
        assert "id" in data

    async def test_without_barcode(self, client: AsyncClient):
        """Product without barcode is allowed"""
        headers = await get_auth_headers(client)
        response = await client.post(f"{PRODUCTS_URL}/create", json={
            "name": "Homemade Jam",
        }, headers=headers)

        assert response.status_code == 201
        assert response.json()["barcode"] is None

    async def test_duplicate_barcode_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        await client.post(f"{PRODUCTS_URL}/create", json=MANUAL_PRODUCT, headers=headers)
        response = await client.post(f"{PRODUCTS_URL}/create", json=MANUAL_PRODUCT, headers=headers)
        assert response.status_code == 409

    async def test_missing_name_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{PRODUCTS_URL}/create", json={"barcode": "111"}, headers=headers)
        assert response.status_code == 422

    async def test_empty_name_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{PRODUCTS_URL}/create", json={"name": ""}, headers=headers)
        assert response.status_code == 422

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.post(f"{PRODUCTS_URL}/create", json=MANUAL_PRODUCT)
        assert response.status_code == 401