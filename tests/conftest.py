import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient, AsyncMongoMockCollection
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import _database


_original_find_one_and_update = AsyncMongoMockCollection.find_one_and_update


async def _find_one_and_update_with_array_filters(self, filter, update, *args, **kwargs):
    """
    mongomock does not support MongoDB array_filters, but the app uses one
    during inventory soft-delete to mark pending notifications as sent.
    Emulate that narrow behavior so integration tests keep using the real
    route/service code while staying on in-memory Mongo.
    """
    array_filters = kwargs.get("array_filters")
    set_update = update.get("$set", {}) if isinstance(update, dict) else {}

    if (
        array_filters == [{"elem.sent": False}]
        and "scheduled_notifications.$[elem].sent" in set_update
    ):
        kwargs = dict(kwargs)
        kwargs.pop("array_filters", None)

        compatible_set = dict(set_update)
        notification_sent = compatible_set.pop("scheduled_notifications.$[elem].sent")
        compatible_update = dict(update)
        if compatible_set:
            compatible_update["$set"] = compatible_set
            result = await _original_find_one_and_update(self, filter, compatible_update, *args, **kwargs)
        else:
            result = await self.find_one(filter)

        if not result:
            return result

        current = await self.find_one({"_id": result["_id"]})
        notifications = current.get("scheduled_notifications", [])
        for notification in notifications:
            if notification.get("sent") is False:
                notification["sent"] = notification_sent

        await self.update_one(
            {"_id": result["_id"]},
            {"$set": {"scheduled_notifications": notifications}},
        )
        return result

    return await _original_find_one_and_update(self, filter, update, *args, **kwargs)


AsyncMongoMockCollection.find_one_and_update = _find_one_and_update_with_array_filters


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def mock_db():
    """
    Replaces real MongoDB to mongomock before every test.
    Clears collections after test
    """
    client = AsyncMongoMockClient()
    db = client["test_food_tracker"]

    _database.client = client
    _database.db = db

    yield db

    # Clear collections after test
    for collection in await db.list_collection_names():
        await db[collection].drop()


@pytest_asyncio.fixture
async def client():
    """
    Async HTTP client for endpoints testing
    Firebase mocks globally.
    """
    with patch("app.core.firebase.init_firebase"), \
         patch("app.modules.notifications.scheduler.start_notification_scheduler", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """
    Creates user.
    Used in tests where user required
    """
    payload = {"name": "Test User", "email": "test@example.com", "password": "strongpassword"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict:
    """
    Returns Authorization header for authorized requests
    """
    response = await client.post("/api/v1/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
