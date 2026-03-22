from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

INVENTORY_URL = "/api/v1/inventory"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

VALID_USER = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "strongpassword",
}

VALID_ITEM = {
    "custom_name": "Milk",
    "category": "dairy",
    "amount": 1.0,
    "unit": "l",
    "expiration_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
}


async def get_auth_headers(client: AsyncClient) -> dict:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def add_item(client: AsyncClient, headers: dict, data: dict = None) -> dict:
    response = await client.post(f"{INVENTORY_URL}/add", json=data or VALID_ITEM, headers=headers)
    assert response.status_code == 201
    return response.json()


class TestAddInventoryItem:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json=VALID_ITEM, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["custom_name"] == VALID_ITEM["custom_name"]
        assert data["amount"] == VALID_ITEM["amount"]
        assert data["unit"] == VALID_ITEM["unit"]
        assert data["status"] == "active"
        assert "id" in data
        assert "scheduled_notifications" in data

    async def test_invalid_unit_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "unit": "invalid_unit",
        }, headers=headers)
        assert response.status_code == 422

    async def test_negative_amount_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "amount": -1.0,
        }, headers=headers)
        assert response.status_code == 422

    async def test_zero_amount_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "amount": 0,
        }, headers=headers)
        assert response.status_code == 422

    async def test_missing_expiration_date_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json={
            "custom_name": "Milk",
            "amount": 1.0,
            "unit": "l",
        }, headers=headers)
        assert response.status_code == 422

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.post(f"{INVENTORY_URL}/add", json=VALID_ITEM)
        assert response.status_code == 401


class TestGetInventory:
    async def test_empty_inventory(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.get(INVENTORY_URL, headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_added_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        await add_item(client, headers)
        await add_item(client, headers, {**VALID_ITEM, "custom_name": "Yogurt"})

        response = await client.get(INVENTORY_URL, headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_filter_by_status(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        # Consume the item
        await client.patch(f"{INVENTORY_URL}/{item['id']}/consume", headers=headers)

        active = await client.get(f"{INVENTORY_URL}?status=active", headers=headers)
        consumed = await client.get(f"{INVENTORY_URL}?status=consumed", headers=headers)

        assert len(active.json()) == 0
        assert len(consumed.json()) == 1

    async def test_deleted_items_not_returned(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)
        await client.delete(f"{INVENTORY_URL}/{item['id']}", headers=headers)

        response = await client.get(INVENTORY_URL, headers=headers)
        assert len(response.json()) == 0

    async def test_user_isolation(self, client: AsyncClient):
        """Users cannot see each other's inventory"""
        headers_1 = await get_auth_headers(client)
        await add_item(client, headers_1)

        # Register second user
        await client.post(REGISTER_URL, json={**VALID_USER, "email": "other@example.com"})
        response = await client.post(LOGIN_URL, json={"email": "other@example.com", "password": VALID_USER["password"]})
        headers_2 = {"Authorization": f"Bearer {response.json()['access_token']}"}

        response = await client.get(INVENTORY_URL, headers=headers_2)
        assert len(response.json()) == 0

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.get(INVENTORY_URL)
        assert response.status_code == 401


class TestGetInventoryItem:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        response = await client.get(f"{INVENTORY_URL}/{item['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == item["id"]

    async def test_not_found(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.get(f"{INVENTORY_URL}/000000000000000000000000", headers=headers)
        assert response.status_code == 404

    async def test_other_user_cannot_access(self, client: AsyncClient):
        headers_1 = await get_auth_headers(client)
        item = await add_item(client, headers_1)

        await client.post(REGISTER_URL, json={**VALID_USER, "email": "other@example.com"})
        response = await client.post(LOGIN_URL, json={"email": "other@example.com", "password": VALID_USER["password"]})
        headers_2 = {"Authorization": f"Bearer {response.json()['access_token']}"}

        response = await client.get(f"{INVENTORY_URL}/{item['id']}", headers=headers_2)
        assert response.status_code == 404


class TestUpdateInventoryItem:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        response = await client.patch(f"{INVENTORY_URL}/{item['id']}", json={
            "custom_name": "Updated Milk",
            "amount": 0.5,
        }, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["custom_name"] == "Updated Milk"
        assert data["amount"] == 0.5

    async def test_empty_update_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        response = await client.patch(f"{INVENTORY_URL}/{item['id']}", json={}, headers=headers)
        assert response.status_code == 400

    async def test_update_expiration_reschedules_notifications(self, client: AsyncClient):
        """Updating expiration date should regenerate scheduled_notifications"""
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)
        old_notifications = item["scheduled_notifications"]

        new_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        response = await client.patch(f"{INVENTORY_URL}/{item['id']}", json={
            "expiration_date": new_date,
        }, headers=headers)

        assert response.status_code == 200
        new_notifications = response.json()["scheduled_notifications"]
        assert new_notifications != old_notifications

    async def test_not_found(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.patch(f"{INVENTORY_URL}/000000000000000000000000", json={
            "custom_name": "Ghost",
        }, headers=headers)
        assert response.status_code == 404


class TestConsumeInventoryItem:
    async def test_success(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        response = await client.patch(f"{INVENTORY_URL}/{item['id']}/consume", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "consumed"

    async def test_not_found(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.patch(f"{INVENTORY_URL}/000000000000000000000000/consume", headers=headers)
        assert response.status_code == 404


class TestDeleteInventoryItem:
    async def test_soft_delete(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)

        response = await client.delete(f"{INVENTORY_URL}/{item['id']}", headers=headers)
        assert response.status_code == 200

        # Item should not appear in inventory list
        inventory = await client.get(INVENTORY_URL, headers=headers)
        assert len(inventory.json()) == 0

    async def test_not_found(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.delete(f"{INVENTORY_URL}/000000000000000000000000", headers=headers)
        assert response.status_code == 404


class TestGetExpiringItems:
    async def test_returns_expiring_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        # Expires in 2 days — should appear with default threshold of 3
        await add_item(client, headers, {
            **VALID_ITEM,
            "custom_name": "Expiring Soon",
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        })

        response = await client.get(f"{INVENTORY_URL}/expiring?days=3", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["custom_name"] == "Expiring Soon"

    async def test_does_not_return_fresh_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        # Expires in 10 days — should not appear with threshold of 3
        await add_item(client, headers, {
            **VALID_ITEM,
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        })

        response = await client.get(f"{INVENTORY_URL}/expiring?days=3", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

    async def test_invalid_days_rejected(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.get(f"{INVENTORY_URL}/expiring?days=0", headers=headers)
        assert response.status_code == 422


class TestInventoryStats:
    async def test_empty_stats(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        response = await client.get(f"{INVENTORY_URL}/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_active"] == 0
        assert data["expiring_today"] == 0
        assert data["expiring_in_3_days"] == 0
        assert data["expired"] == 0

    async def test_counts_active_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        await add_item(client, headers)
        await add_item(client, headers, {**VALID_ITEM, "custom_name": "Yogurt"})

        response = await client.get(f"{INVENTORY_URL}/stats", headers=headers)
        assert response.json()["total_active"] == 2

    async def test_counts_expiring_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        await add_item(client, headers, {
            **VALID_ITEM,
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        })
        # Fresh item — should not be counted
        await add_item(client, headers, {
            **VALID_ITEM,
            "custom_name": "Fresh",
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        })

        response = await client.get(f"{INVENTORY_URL}/stats", headers=headers)
        data = response.json()
        assert data["expiring_in_3_days"] == 1
        assert data["total_active"] == 2

    async def test_counts_expired_items(self, client: AsyncClient):
        headers = await get_auth_headers(client)

        await add_item(client, headers, {
            **VALID_ITEM,
            "expiration_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        })

        response = await client.get(f"{INVENTORY_URL}/stats", headers=headers)
        assert response.json()["expired"] == 1

    async def test_consumed_not_counted(self, client: AsyncClient):
        headers = await get_auth_headers(client)
        item = await add_item(client, headers)
        await client.patch(f"{INVENTORY_URL}/{item['id']}/consume", headers=headers)

        response = await client.get(f"{INVENTORY_URL}/stats", headers=headers)
        assert response.json()["total_active"] == 0