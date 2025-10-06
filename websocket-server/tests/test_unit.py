from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from websocket_server.handlers.message_handler import MessageHandler
from websocket_server.handlers.websocket_handler import WebSocketHandler
from websocket_server.util import (check_rate_limit, generate_token,
                                   validate_token)


class TestMessageHandler:
    """Unit tests for MessageHandler class"""

    @pytest.fixture
    def message_handler(self):
        return MessageHandler()

    @pytest.mark.asyncio
    async def test_process_message_success(self, message_handler):
        """Test successful message processing"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=True), \
             patch('websocket_server.handlers.message_handler.kafka_helper') as mock_kafka:

            data = {
                "type": "message",
                "content": "Hello, World!",
            }
            userid = "testuser"

            result = await message_handler.process_message(data, userid)

            assert result is None  # No error
            mock_kafka.publish.assert_called_once()

            # Verify kafka message structure
            call_args = mock_kafka.publish.call_args[0]
            kafka_message = call_args[1]
            assert kafka_message["type"] == "message"
            assert kafka_message["content"] == "Hello, World!"
            assert kafka_message["userid"] == "testuser"

    @pytest.mark.asyncio
    async def test_process_message_invalid_type(self, message_handler):
        """Test message with invalid type"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=True):
            data = {
                "type": "invalid",
                "content": "Hello",
            }
            userid = "testuser"

            result = await message_handler.process_message(data, userid)

            assert result is not None
            assert result["type"] == "error"
            assert "Invalid message format" in result["message"]

    @pytest.mark.asyncio
    async def test_process_message_missing_content(self, message_handler):
        """Test message with missing content"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=True):
            data = {
                "type": "message",
            }
            userid = "testuser"

            result = await message_handler.process_message(data, userid)

            assert result is not None
            assert result["type"] == "error"
            assert "Invalid message format" in result["message"]

    @pytest.mark.asyncio
    async def test_process_message_rate_limited(self, message_handler):
        """Test message when user is rate limited"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=False):
            data = {
                "type": "message",
                "content": "Hello",
            }
            userid = "testuser"

            result = await message_handler.process_message(data, userid)

            assert result is not None
            assert result["type"] == "error"
            assert "Rate limit exceeded" in result["message"]

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, message_handler):
        """Test rate limit check when allowed"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=True):
            result = await message_handler.check_rate_limit("testuser")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, message_handler):
        """Test rate limit check when exceeded"""
        with patch('websocket_server.handlers.message_handler.check_rate_limit', return_value=False):
            result = await message_handler.check_rate_limit("testuser")
            assert result is False


class TestWebSocketHandler:
    """Unit tests for WebSocketHandler class"""

    @pytest.fixture
    def ws_handler(self):
        return WebSocketHandler()

    @pytest.mark.asyncio
    async def test_connect_new_user(self, ws_handler):
        """Test connecting a new user"""
        mock_websocket = AsyncMock()
        userid = "testuser"

        with patch('websocket_server.handlers.websocket_handler.redis_helper') as mock_redis:
            mock_redis.subscribe = AsyncMock()

            await ws_handler.connect(mock_websocket, userid)

            mock_websocket.accept.assert_called_once()
            assert userid in ws_handler.active_connections
            assert mock_websocket in ws_handler.active_connections[userid]
            mock_redis.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_existing_user(self, ws_handler):
        """Test connecting an existing user (multiple connections)"""
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        userid = "testuser"

        with patch('websocket_server.handlers.websocket_handler.redis_helper') as mock_redis:
            mock_redis.subscribe = AsyncMock()

            # First connection
            await ws_handler.connect(mock_websocket1, userid)
            # Second connection
            await ws_handler.connect(mock_websocket2, userid)

            assert len(ws_handler.active_connections[userid]) == 2
            # Redis subscribe should only be called once for the first connection
            assert mock_redis.subscribe.call_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_one_connection(self, ws_handler):
        """Test disconnecting one connection when user has multiple"""
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        userid = "testuser"

        with patch('websocket_server.handlers.websocket_handler.redis_helper') as mock_redis:
            mock_redis.subscribe = AsyncMock()
            mock_redis.unsubscribe = AsyncMock()

            # Setup two connections
            await ws_handler.connect(mock_websocket1, userid)
            await ws_handler.connect(mock_websocket2, userid)

            # Disconnect one
            await ws_handler.disconnect(mock_websocket1, userid)

            assert userid in ws_handler.active_connections
            assert len(ws_handler.active_connections[userid]) == 1
            assert mock_websocket2 in ws_handler.active_connections[userid]
            # Should not unsubscribe from Redis yet
            mock_redis.unsubscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_last_connection(self, ws_handler):
        """Test disconnecting the last connection for a user"""
        mock_websocket = AsyncMock()
        userid = "testuser"

        with patch('websocket_server.handlers.websocket_handler.redis_helper') as mock_redis:
            mock_redis.subscribe = AsyncMock()
            mock_redis.unsubscribe = AsyncMock()

            # Setup connection
            await ws_handler.connect(mock_websocket, userid)

            # Disconnect
            await ws_handler.disconnect(mock_websocket, userid)

            assert userid not in ws_handler.active_connections
            # Should unsubscribe from Redis
            mock_redis.unsubscribe.assert_called_once_with(userid)

    @pytest.mark.asyncio
    async def test_broadcast_message(self, ws_handler):
        """Test broadcasting message to user connections"""
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        userid = "testuser"
        channel = f"user:{userid}"

        with patch('websocket_server.handlers.websocket_handler.redis_helper') as mock_redis:
            mock_redis.subscribe = AsyncMock()

            # Setup connections
            await ws_handler.connect(mock_websocket1, userid)
            await ws_handler.connect(mock_websocket2, userid)

            # Broadcast message
            message = {
                "data": '{"type": "response", "content": "Hello", "correlation_id": "123"}'
            }
            await ws_handler.broadcast(channel, message)

            # Both connections should receive the message
            assert mock_websocket1.send_json.call_count == 1
            assert mock_websocket2.send_json.call_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_disconnected_user(self, ws_handler):
        """Test broadcasting to a user who has disconnected"""
        userid = "testuser"
        channel = f"user:{userid}"

        message = {
            "data": '{"type": "response", "content": "Hello", "correlation_id": "123"}'
        }

        # Broadcast to non-existent user should not raise error
        await ws_handler.broadcast(channel, message)

        # Should complete without error
        assert userid not in ws_handler.active_connections


class TestUtilFunctions:
    """Unit tests for utility functions"""

    @pytest.mark.asyncio
    async def test_validate_token_valid(self):
        """Test validating a valid token"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.get = AsyncMock(return_value="testuser")

            result = await validate_token("valid_token", "testuser")

            assert result is True
            mock_redis.get.assert_called_once_with("token:valid_token")

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self):
        """Test validating an invalid token"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.get = AsyncMock(return_value="otheruser")

            result = await validate_token("token", "testuser")

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_token_not_found(self):
        """Test validating a token that doesn't exist"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            result = await validate_token("nonexistent", "testuser")

            assert result is False

    @pytest.mark.asyncio
    async def test_generate_token(self):
        """Test generating a new token"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.set = AsyncMock()

            token = await generate_token("testuser")

            assert len(token) > 0
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args[0]
            assert call_args[0].startswith("token:")
            assert call_args[1] == "testuser"

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()

            result = await check_rate_limit("testuser")

            assert result is True
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self):
        """Test rate limit check when within limit"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            mock_redis.get = AsyncMock(return_value="5")
            mock_redis.incr = AsyncMock()

            result = await check_rate_limit("testuser")

            assert result is True
            mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded"""
        with patch('websocket_server.util.redis_helper') as mock_redis:
            # Mock settings to have a max of 10 requests
            with patch('websocket_server.util.settings') as mock_settings:
                mock_settings.user_rate_limit_max_requests = 10
                mock_redis.get = AsyncMock(return_value="10")

                result = await check_rate_limit("testuser")

                assert result is False
                mock_redis.incr.assert_not_called()
