import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from websocket_server.main import app
from websocket_server.util import redis_helper, kafka_helper


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_client():
    """Create a test client for the FastAPI app"""
    # Initialize for async tests
    await redis_helper.initialize()
    kafka_helper.initialize()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Cleanup for async tests
    if redis_helper.redis_client:
        async for key in redis_helper.redis_client.scan_iter("token:*"):
            await redis_helper.redis_client.delete(key)
        async for key in redis_helper.redis_client.scan_iter("rate_limit:*"):
            await redis_helper.redis_client.delete(key)


@pytest.fixture(scope="function")
def sync_client():
    """Create a synchronous test client for WebSocket testing"""
    # TestClient handles its own event loop and lifespan
    with TestClient(app) as client:
        yield client
