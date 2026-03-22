from httpx import AsyncClient


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
FCM_URL = "/api/v1/auth/fcm-token"
NOTIFICATION_SETTINGS_URL = "/api/v1/auth/notification-settings"

VALID_USER = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "strongpassword",
}


# region Helpers

async def register(client: AsyncClient, data: dict = None) -> dict:
    response = await client.post(REGISTER_URL, json=data or VALID_USER)
    return response


async def login(client: AsyncClient, email: str = VALID_USER["email"], password: str = VALID_USER["password"]) -> dict:
    response = await client.post(LOGIN_URL, json={"email": email, "password": password})
    return response


async def get_auth_headers(client: AsyncClient) -> dict:
    await register(client)
    response = await login(client)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# endregion Helpers


class TestRegister:
    async def test_success(self, client: AsyncClient):
        response = await register(client)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == VALID_USER["name"]
        assert data["email"] == VALID_USER["email"]
        assert "id" in data
        assert "password" not in data

    async def test_duplicate_email(self, client: AsyncClient):
        await register(client)
        response = await register(client)
        assert response.status_code == 409

    async def test_invalid_email(self, client: AsyncClient):
        response = await register(client, {**VALID_USER, "email": "not-an-email"})
        assert response.status_code == 422

    async def test_short_password(self, client: AsyncClient):
        response = await register(client, {**VALID_USER, "password": "123"})
        assert response.status_code == 422

    async def test_short_name(self, client: AsyncClient):
        response = await register(client, {**VALID_USER, "name": "ab"})
        assert response.status_code == 422

    async def test_missing_fields(self, client: AsyncClient):
        response = await client.post(REGISTER_URL, json={"email": VALID_USER["email"]})
        assert response.status_code == 422


class TestLogin:
    async def test_success(self, client: AsyncClient):
        await register(client)
        response = await login(client)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password(self, client: AsyncClient):
        await register(client)
        response = await login(client, password="wrongpassword")
        assert response.status_code == 401

    async def test_unknown_email(self, client: AsyncClient):
        response = await login(client, email="unknown@example.com")
        assert response.status_code == 401

    async def test_invalid_email_format(self, client: AsyncClient):
        response = await client.post(LOGIN_URL, json={"email": "notanemail", "password": "password"})
        assert response.status_code == 422


class TestGetMe:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.get(ME_URL, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == VALID_USER["email"]
        assert data["name"] == VALID_USER["name"]
        assert "notification_days_before" in data
        assert "created_at" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.get(ME_URL)
        assert response.status_code == 401

    async def test_invalid_token(self, client: AsyncClient):
        response = await client.get(ME_URL, headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 401


class TestUpdateFCMToken:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.patch(FCM_URL, json={"fcm_token": "new_fcm_token_123"}, headers=headers)
        assert response.status_code == 200

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.patch(FCM_URL, json={"fcm_token": "token"})
        assert response.status_code == 401

    async def test_token_reflected_in_me(self, client: AsyncClient):
        """After FCM token update it should be visible in /me response"""
        headers = await get_auth_headers(client)
        await client.patch(FCM_URL, json={"fcm_token": "my_test_token"}, headers=headers)
        response = await client.get(ME_URL, headers=headers)
        assert response.json()["fcm_token"] == "my_test_token"


class TestUpdateNotificationSettings:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"notification_days_before": [7, 3, 1]},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_reflected_in_me(self, client: AsyncClient):
        """After update notification settings should be visible in /me response"""
        headers = await get_auth_headers(client)
        new_settings = [7, 3, 1]
        await client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"notification_days_before": new_settings},
            headers=headers,
        )
        response = await client.get(ME_URL, headers=headers)
        assert response.json()["notification_days_before"] == new_settings

    async def test_empty_list_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"notification_days_before": []},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"notification_days_before": [3, 1]},
        )
        assert response.status_code == 401