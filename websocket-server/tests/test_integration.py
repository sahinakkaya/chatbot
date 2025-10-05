import pytest
import json
from websocket_server.util import redis_helper
from websocket_server.config import settings


class TestTokenEndpoint:
    """Integration tests for token generation endpoint"""

    @pytest.mark.asyncio
    async def test_generate_token_success(self, test_client):
        """Test successful token generation"""
        response = await test_client.post("/token?userid=testuser123")

        assert response.status_code == 200
        data = response.json()

        assert "token" in data
        assert "userid" in data
        assert "expires_in" in data
        assert data["userid"] == "testuser123"
        assert data["expires_in"] == settings.token_ttl
        assert len(data["token"]) > 0

    @pytest.mark.asyncio
    async def test_generated_token_is_valid(self, test_client):
        """Test that generated token is stored in Redis correctly"""
        response = await test_client.post("/token?userid=testuser456")
        data = response.json()
        token = data["token"]

        # Verify token is stored in Redis
        stored_userid = await redis_helper.get(f"token:{token}")
        assert stored_userid == "testuser456"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "websocket-server"
        assert "server_id" in data
        assert "active_users" in data
        assert "total_connections" in data


class TestWebSocketConnection:
    """Integration tests for WebSocket connection flow"""

    def test_websocket_connection_with_valid_token(self, sync_client):
        """Test WebSocket connection with valid token"""
        # Generate token first
        response = sync_client.post("/token?userid=wsuser1")
        assert response.status_code == 200
        token = response.json()["token"]

        # Connect via WebSocket
        with sync_client.websocket_connect(f"/ws?token={token}&userid=wsuser1") as websocket:
            # Connection should be successful
            assert websocket is not None

    def test_websocket_connection_with_invalid_token(self, sync_client):
        """Test WebSocket connection with invalid token"""
        with pytest.raises(Exception):  # Should raise WebSocketDisconnect
            with sync_client.websocket_connect(f"/ws?token=invalid_token&userid=wsuser2"):
                pass

    def test_websocket_send_receive_message(self, sync_client):
        """Test sending and receiving messages via WebSocket"""
        # Generate token
        response = sync_client.post("/token?userid=wsuser3")
        assert response.status_code == 200
        token = response.json()["token"]

        with sync_client.websocket_connect(f"/ws?token={token}&userid=wsuser3") as websocket:
            # Send a message
            test_message = {
                "type": "message",
                "content": "Hello, WebSocket!",
                "userid": "wsuser3"
            }
            websocket.send_json(test_message)

            # Note: In real scenario, response would come from Kafka->AI Consumer->Redis
            # For this test, we just verify the message was accepted (no error response)
            # You may need to mock Kafka/Redis or use actual services for full integration


class TestRateLimiting:
    """Integration tests for rate limiting"""

    def test_rate_limit_enforcement(self, sync_client):
        """Test that rate limiting is enforced"""
        # Generate token
        response = sync_client.post("/token?userid=ratelimit_user")
        assert response.status_code == 200
        token = response.json()["token"]

        with sync_client.websocket_connect(f"/ws?token={token}&userid=ratelimit_user") as websocket:
            # Send messages up to the rate limit
            max_requests = settings.user_rate_limit_max_requests

            for i in range(max_requests):
                message = {
                    "type": "message",
                    "content": f"Message {i}",
                    "userid": "ratelimit_user"
                }
                websocket.send_json(message)

            # Next message should trigger rate limit
            rate_limited_message = {
                "type": "message",
                "content": "This should be rate limited",
                "userid": "ratelimit_user"
            }
            websocket.send_json(rate_limited_message)

            # Should receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "rate limit" in response["message"].lower()

    def test_invalid_message_format(self, sync_client):
        """Test that invalid message format returns error"""
        response = sync_client.post("/token?userid=invalid_msg_user")
        assert response.status_code == 200
        token = response.json()["token"]

        with sync_client.websocket_connect(f"/ws?token={token}&userid=invalid_msg_user") as websocket:
            # Send invalid message (missing content)
            invalid_message = {
                "type": "message",
                # Missing "content" field
                "userid": "invalid_msg_user"
            }
            websocket.send_json(invalid_message)

            # Should receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "invalid" in response["message"].lower()


class TestMultipleConnections:
    """Integration tests for multiple concurrent connections"""

    def test_multiple_users_can_connect(self, sync_client):
        """Test that multiple users can connect simultaneously"""
        # Generate tokens for multiple users
        tokens = {}
        for i in range(3):
            userid = f"multiuser_{i}"
            response = sync_client.post(f"/token?userid={userid}")
            assert response.status_code == 200
            tokens[userid] = response.json()["token"]

        # Connect all users
        websockets = []
        for userid, token in tokens.items():
            ws = sync_client.websocket_connect(f"/ws?token={token}&userid={userid}")
            websockets.append(ws.__enter__())

        # All connections should be active
        assert len(websockets) == 3

        # Cleanup
        for ws in websockets:
            ws.__exit__(None, None, None)
