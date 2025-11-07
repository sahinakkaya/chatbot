import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from message_relay.dependencies import MessageRelayService


class TestMessageRelayService:
    """Unit tests for MessageRelayService class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch("message_relay.dependencies.settings") as mock_settings:
            mock_settings.consume_topic = "responses"
            yield mock_settings

    @pytest.fixture
    def relay_service(self, mock_settings):
        """Create MessageRelayService instance with mocked dependencies"""
        with (
            patch("message_relay.dependencies.KafkaHelper"),
            patch("message_relay.dependencies.RedisHelper"),
        ):
            service = MessageRelayService()
            service.kafka_helper = MagicMock()
            service.redis_helper = AsyncMock()
            return service

    def test_initialization(self, mock_settings):
        """Test MessageRelayService initialization"""
        with (
            patch("message_relay.dependencies.KafkaHelper") as mock_kafka,
            patch("message_relay.dependencies.RedisHelper") as mock_redis,
        ):
            service = MessageRelayService()

            # Verify KafkaHelper was initialized
            mock_kafka.assert_called_once_with(mock_settings)
            mock_kafka.return_value.initialize.assert_called_once_with(
                consumer_args={
                    "group_id": "message-relay-group",
                    "auto_offset_reset": "earliest",
                }
            )

            # Verify RedisHelper was created
            mock_redis.assert_called_once_with(mock_settings)

    @pytest.mark.asyncio
    async def test_process_message_success(self, relay_service):
        """Test successful message processing"""
        relay_service.redis_helper.publish = AsyncMock(return_value=2)  # 2 subscribers

        message = {"userid": "testuser", "type": "response", "content": "Hello from AI"}

        await relay_service.process_message(message)

        # Verify publish_to_redis was called
        relay_service.redis_helper.publish.assert_called_once()
        call_args = relay_service.redis_helper.publish.call_args[0]

        # Verify channel format
        assert call_args[0] == "user:testuser"

        # Verify message was JSON serialized
        published_message = json.loads(call_args[1])
        assert published_message["userid"] == "testuser"
        assert published_message["type"] == "response"
        assert published_message["content"] == "Hello from AI"

    @pytest.mark.asyncio
    async def test_process_message_missing_userid(self, relay_service):
        """Test message processing with missing userid"""
        message = {"type": "response", "content": "Hello"}

        await relay_service.process_message(message)

        # Should not call publish when userid is missing
        relay_service.redis_helper.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_adds_default_type(self, relay_service):
        """Test that default type is added if missing"""
        relay_service.redis_helper.publish = AsyncMock(return_value=1)

        message = {
            "userid": "testuser",
            "content": "Hello",
            # No "type" field
        }

        await relay_service.process_message(message)

        # Verify type was added
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["type"] == "response"

    @pytest.mark.asyncio
    async def test_process_message_redis_failure(self, relay_service):
        """Test message processing when Redis publish fails"""
        relay_service.redis_helper.publish = AsyncMock(
            side_effect=Exception("Redis connection error")
        )

        message = {"userid": "testuser", "type": "response", "content": "Hello"}

        # Should not raise exception (error is caught and logged)
        await relay_service.process_message(message)

    @pytest.mark.asyncio
    async def test_publish_to_redis_success(self, relay_service):
        """Test successful Redis publish"""
        relay_service.redis_helper.publish = AsyncMock(return_value=3)

        message = {"userid": "testuser", "type": "response", "content": "Test message"}

        await relay_service.publish_to_redis("testuser", message)

        # Verify publish was called with correct channel
        relay_service.redis_helper.publish.assert_called_once()
        call_args = relay_service.redis_helper.publish.call_args[0]
        assert call_args[0] == "user:testuser"

        # Verify message structure
        published_message = json.loads(call_args[1])
        assert published_message["userid"] == "testuser"
        assert published_message["type"] == "response"
        assert published_message["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_publish_to_redis_zero_subscribers(self, relay_service):
        """Test Redis publish with zero subscribers"""
        relay_service.redis_helper.publish = AsyncMock(return_value=0)

        message = {
            "userid": "testuser",
            "type": "response",
            "content": "No one listening",
        }

        # Should complete without error even with 0 subscribers
        await relay_service.publish_to_redis("testuser", message)

        relay_service.redis_helper.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_to_redis_adds_type_if_missing(self, relay_service):
        """Test that publish_to_redis adds type if not present"""
        relay_service.redis_helper.publish = AsyncMock(return_value=1)

        message = {"userid": "testuser", "content": "Message without type"}

        await relay_service.publish_to_redis("testuser", message)

        # Verify type was added
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["type"] == "response"

    @pytest.mark.asyncio
    async def test_publish_to_redis_failure(self, relay_service):
        """Test Redis publish failure handling"""
        relay_service.redis_helper.publish = AsyncMock(
            side_effect=Exception("Redis error")
        )

        message = {"userid": "testuser", "type": "response", "content": "Test"}

        # Should raise exception
        with pytest.raises(Exception, match="Redis error"):
            await relay_service.publish_to_redis("testuser", message)

    @pytest.mark.asyncio
    async def test_cleanup(self, relay_service):
        """Test cleanup method"""
        await relay_service.cleanup()

        # Verify Kafka was torn down
        relay_service.kafka_helper.teardown.assert_called_once()

        # Verify Redis was torn down
        relay_service.redis_helper.teardown.assert_called_once()


class TestMessageFormats:
    """Test various message format scenarios"""

    @pytest.fixture
    def relay_service(self):
        """Create MessageRelayService with mocked dependencies"""
        with (
            patch("message_relay.dependencies.KafkaHelper"),
            patch("message_relay.dependencies.RedisHelper"),
        ):
            service = MessageRelayService()
            service.kafka_helper = MagicMock()
            service.redis_helper = AsyncMock()
            service.redis_helper.publish = AsyncMock(return_value=1)
            return service

    @pytest.mark.asyncio
    async def test_message_with_extra_fields(self, relay_service):
        """Test message with additional fields is preserved"""
        message = {
            "userid": "testuser",
            "type": "response",
            "content": "Hello",
            "timestamp": "2024-01-01T00:00:00",
            "processing_time_ms": 100,
            "correlation_id": "abc-123",
        }

        await relay_service.publish_to_redis("testuser", message)

        # Verify all fields are preserved
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["timestamp"] == "2024-01-01T00:00:00"
        assert published_message["processing_time_ms"] == 100
        assert published_message["correlation_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_message_with_special_characters(self, relay_service):
        """Test message with special characters"""
        message = {
            "userid": "testuser",
            "type": "response",
            "content": "Hello 你好 🎉\n\tSpecial: @#$%",
        }

        await relay_service.publish_to_redis("testuser", message)

        # Verify special characters are preserved through JSON serialization
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["content"] == "Hello 你好 🎉\n\tSpecial: @#$%"

    @pytest.mark.asyncio
    async def test_message_with_nested_objects(self, relay_service):
        """Test message with nested objects"""
        message = {
            "userid": "testuser",
            "type": "response",
            "content": "Hello",
            "metadata": {"source": "ai", "model": "gpt-3.5-turbo", "tokens": 100},
        }

        await relay_service.publish_to_redis("testuser", message)

        # Verify nested objects are preserved
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["metadata"]["source"] == "ai"
        assert published_message["metadata"]["model"] == "gpt-3.5-turbo"
        assert published_message["metadata"]["tokens"] == 100

    @pytest.mark.asyncio
    async def test_empty_content(self, relay_service):
        """Test message with empty content"""
        message = {"userid": "testuser", "type": "response", "content": ""}

        await relay_service.publish_to_redis("testuser", message)

        # Should handle empty content
        call_args = relay_service.redis_helper.publish.call_args[0]
        published_message = json.loads(call_args[1])
        assert published_message["content"] == ""
