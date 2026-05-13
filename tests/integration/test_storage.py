from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

STORAGE_URL = "/api/v1/storage"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

VALID_USER = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "strongpassword",
}


async def get_auth_headers(client: AsyncClient) -> dict:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestStorageRecommendations:
    async def test_seed_recommendation(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        with patch("app.modules.storage.service.fetch_storage_recommendation", new_callable=AsyncMock) as mock_gemini:
            response = await client.post(
                f"{STORAGE_URL}/recommendations",
                json={"name": "яблоко", "location": "fridge", "state": "whole"},
                headers=headers,
            )

        assert response.status_code == 200
        mock_gemini.assert_not_called()
        data = response.json()
        assert data["canonical_name"] == "apple"
        assert data["recommended_days"] == 30
        assert data["source"] == "database"
        assert data["is_verified"] is True

    async def test_gemini_fallback_is_cached(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        gemini_response = {
            "canonical_name": "cloudberry",
            "display_name_en": "Cloudberry",
            "display_name_ru": "Морошка",
            "category": "fruits",
            "aliases": ["cloudberry", "морошка"],
            "rules": [
                {
                    "location": "fridge",
                    "state": "whole",
                    "recommended_days": 4,
                    "min_days": 2,
                    "max_days": 5,
                    "is_default": True,
                }
            ],
            "confidence": 0.7,
        }

        with patch(
            "app.modules.storage.service.fetch_storage_recommendation",
            new_callable=AsyncMock,
            return_value=gemini_response,
        ) as mock_gemini:
            first = await client.post(
                f"{STORAGE_URL}/recommendations",
                json={"name": "морошка"},
                headers=headers,
            )
            second = await client.post(
                f"{STORAGE_URL}/recommendations",
                json={"name": "cloudberry"},
                headers=headers,
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert mock_gemini.call_count == 1
        assert first.json()["source"] == "gemini"
        assert second.json()["recommended_days"] == 4

    async def test_gemini_failure_returns_404(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        with patch(
            "app.modules.storage.service.fetch_storage_recommendation",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.post(
                f"{STORAGE_URL}/recommendations",
                json={"name": "unknown product xyz"},
                headers=headers,
            )

        assert response.status_code == 404

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.post(f"{STORAGE_URL}/recommendations", json={"name": "яблоко"})
        assert response.status_code == 401
