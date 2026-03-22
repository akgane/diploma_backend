from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

INVENTORY_URL = "/api/v1/inventory"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
FCM_URL = "/api/v1/auth/fcm-token"

VALID_USER = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "strongpassword",
}

VALID_ITEM = {
    "custom_name": "Milk",
    "amount": 1.0,
    "unit": "l",
    "expiration_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
}


async def set_notifications_in_past(mock_db) -> None:
    """Helper to move all scheduled notification send_at to the past"""
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    items = await mock_db["inventory_items"].find({}).to_list(length=100)
    for item in items:
        notifications = item.get("scheduled_notifications", [])
        for n in notifications:
            n["send_at"] = past
        await mock_db["inventory_items"].update_one(
            {"_id": item["_id"]},
            {"$set": {"scheduled_notifications": notifications}}
        )


async def get_auth_headers(client: AsyncClient) -> dict:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def set_fcm_token(client: AsyncClient, headers: dict, token: str = "test_fcm_token") -> None:
    await client.patch(FCM_URL, json={"fcm_token": token}, headers=headers)


class TestScheduledNotifications:
    async def test_notifications_scheduled_on_add(self, client: AsyncClient):
        """Adding item with future expiration date creates scheduled notifications"""
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json=VALID_ITEM, headers=headers)

        assert response.status_code == 201
        notifications = response.json()["scheduled_notifications"]
        assert len(notifications) == 3
        assert all(n["sent"] is False for n in notifications)

    async def test_notification_thresholds_correct(self, client: AsyncClient):
        """Scheduled notifications match user default thresholds [3, 1, 0.5]"""
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json=VALID_ITEM, headers=headers)

        notifications = response.json()["scheduled_notifications"]
        thresholds = sorted([n["threshold"] for n in notifications], reverse=True)
        assert thresholds == [3.0, 1.0, 0.5]

    async def test_past_thresholds_not_scheduled(self, client: AsyncClient):
        """If expiration is in 1 day, threshold=3 is in the past and skipped"""
        headers = await get_auth_headers(client)
        response = await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }, headers=headers)

        notifications = response.json()["scheduled_notifications"]
        # threshold=3 and threshold=1 are in the past, only 0.5 remains
        assert len(notifications) == 1
        assert notifications[0]["threshold"] == 0.5

    async def test_notifications_rescheduled_on_expiration_update(self, client: AsyncClient):
        """Updating expiration date regenerates scheduled notifications"""
        headers = await get_auth_headers(client)
        item_response = await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }, headers=headers)

        item_id = item_response.json()["id"]
        old_notifications = item_response.json()["scheduled_notifications"]

        new_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        update_response = await client.patch(f"{INVENTORY_URL}/{item_id}", json={
            "expiration_date": new_date,
        }, headers=headers)

        new_notifications = update_response.json()["scheduled_notifications"]
        assert len(new_notifications) > len(old_notifications)


class TestSendExpirationNotification:
    async def test_no_notifications_when_no_items(self, client: AsyncClient, mock_db):
        """Scheduler does nothing when there are no pending notifications"""
        from app.modules.notifications.service import send_expiration_notification

        with patch("app.modules.notifications.service.send_push_notification", new_callable=AsyncMock) as mock_push:
            await send_expiration_notification(mock_db)
            mock_push.assert_not_called()

    async def test_no_notification_without_fcm_token(self, client: AsyncClient, mock_db):
        """User without FCM token does not receive notification"""
        from app.modules.notifications.service import send_expiration_notification

        headers = await get_auth_headers(client)

        # Add item with past send_at to trigger notification
        exp = datetime.now(timezone.utc) + timedelta(days=10)
        await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": exp.isoformat(),
        }, headers=headers)

        # Manually set send_at to past so scheduler picks it up
        await set_notifications_in_past(mock_db)

        with patch("app.modules.notifications.service.send_push_notification", new_callable=AsyncMock) as mock_push:
            await send_expiration_notification(mock_db)
            mock_push.assert_not_called()

    async def test_notification_sent_with_fcm_token(self, client: AsyncClient, mock_db):
        """User with FCM token receives notification for expiring item"""
        from app.modules.notifications.service import send_expiration_notification

        headers = await get_auth_headers(client)
        await set_fcm_token(client, headers)

        # Use future date so notifications are actually scheduled
        exp = datetime.now(timezone.utc) + timedelta(days=10)
        await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": exp.isoformat(),
        }, headers=headers)

        await set_notifications_in_past(mock_db)

        with patch("app.modules.notifications.service.send_push_notification", new_callable=AsyncMock,
                   return_value=True) as mock_push:
            await send_expiration_notification(mock_db)
            assert mock_push.called

    async def test_notification_marked_as_sent(self, client: AsyncClient, mock_db):
        """After successful send, notification is marked as sent=True"""
        from app.modules.notifications.service import send_expiration_notification

        headers = await get_auth_headers(client)
        await set_fcm_token(client, headers)

        exp = datetime.now(timezone.utc) + timedelta(days=10)
        await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": exp.isoformat(),
        }, headers=headers)

        await set_notifications_in_past(mock_db)

        with patch("app.modules.notifications.service.send_push_notification", new_callable=AsyncMock,
                   return_value=True):
            await send_expiration_notification(mock_db)

        item = await mock_db["inventory_items"].find_one({})
        sent_flags = [n["sent"] for n in item["scheduled_notifications"]]
        assert all(sent_flags)

    async def test_notification_not_sent_twice(self, client: AsyncClient, mock_db):
        """Already sent notifications are not sent again"""
        from app.modules.notifications.service import send_expiration_notification

        headers = await get_auth_headers(client)
        await set_fcm_token(client, headers)

        exp = datetime.now(timezone.utc) + timedelta(days=10)
        await client.post(f"{INVENTORY_URL}/add", json={
            **VALID_ITEM,
            "expiration_date": exp.isoformat(),
        }, headers=headers)

        await set_notifications_in_past(mock_db)

        with patch("app.modules.notifications.service.send_push_notification", new_callable=AsyncMock,
                   return_value=True) as mock_push:
            await send_expiration_notification(mock_db)
            first_call_count = mock_push.call_count

            await send_expiration_notification(mock_db)
            assert mock_push.call_count == first_call_count
