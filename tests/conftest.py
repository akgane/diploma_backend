import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.database import _database


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