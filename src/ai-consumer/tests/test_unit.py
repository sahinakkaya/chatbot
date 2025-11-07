from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_consumer.dependencies import AIConsumer


class TestAIConsumer:
    """Unit tests for AIConsumer class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch("ai_consumer.dependencies.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.max_workers = 5
            mock_settings.consume_topic = "incoming_messages"
            mock_settings.produce_topic = "responses"
            yield mock_settings

    @pytest.fixture
    def ai_consumer(self, mock_settings):
        """Create AIConsumer instance with mocked dependencies"""
        with (
            patch("ai_consumer.dependencies.KafkaHelper"),
            patch("ai_consumer.dependencies.OpenAI"),
            patch("ai_consumer.dependencies.ThreadPoolExecutor"),
        ):
            consumer = AIConsumer()
            consumer.kafka_helper = MagicMock()
            consumer.openai_client = MagicMock()
            consumer.executor = MagicMock()
            return consumer

    def test_initialization(self, mock_settings):
        """Test AIConsumer initialization"""
        with (
            patch("ai_consumer.dependencies.KafkaHelper") as mock_kafka,
            patch("ai_consumer.dependencies.OpenAI") as mock_openai,
            patch("ai_consumer.dependencies.ThreadPoolExecutor") as mock_executor,
        ):
            consumer = AIConsumer()

            # Verify KafkaHelper was initialized
            mock_kafka.assert_called_once_with(mock_settings)
            mock_kafka.return_value.initialize.assert_called_once()

            # Verify OpenAI client was created
            mock_openai.assert_called_once_with(
                api_key=mock_settings.openai_api_key, max_retries=0
            )

            # Verify ThreadPoolExecutor was created
            mock_executor.assert_called_once_with(max_workers=mock_settings.max_workers)

    def test_process_message_success(self, ai_consumer):
        """Test successful message processing"""
        with patch.object(
            ai_consumer, "process_with_openai", return_value="AI response here"
        ):
            message = {
                "userid": "testuser",
                "content": "Hello AI",
                "correlation_id": "test-123",
            }

            ai_consumer.process_message(message)

            # Verify OpenAI was called with content
            ai_consumer.process_with_openai.assert_called_once_with("Hello AI")

            # Verify Kafka publish was called
            ai_consumer.kafka_helper.publish.assert_called_once()
            call_args = ai_consumer.kafka_helper.publish.call_args[0]

            # Verify published message structure
            assert (
                call_args[0] == ai_consumer.kafka_helper.publish.call_args[0][0]
            )  # topic
            response_msg = call_args[1]
            assert response_msg["type"] == "response"
            assert response_msg["content"] == "AI response here"
            assert response_msg["userid"] == "testuser"
            assert response_msg["correlation_id"] == "test-123"
            assert "timestamp" in response_msg
            assert "processing_time_ms" in response_msg

    def test_process_message_missing_userid(self, ai_consumer):
        """Test message processing with missing userid"""
        with patch.object(
            ai_consumer, "process_with_openai", return_value="AI response"
        ):
            message = {"content": "Hello", "correlation_id": "test-123"}

            # Should still process but userid will be None
            ai_consumer.process_message(message)

            # Verify it was published
            ai_consumer.kafka_helper.publish.assert_called_once()
            response_msg = ai_consumer.kafka_helper.publish.call_args[0][1]
            assert response_msg["userid"] is None

    def test_process_message_openai_failure(self, ai_consumer):
        """Test message processing when OpenAI fails"""
        with patch.object(
            ai_consumer, "process_with_openai", side_effect=Exception("OpenAI error")
        ):
            message = {
                "userid": "testuser",
                "content": "Hello",
                "correlation_id": "test-123",
            }

            # Should raise exception
            with pytest.raises(Exception, match="OpenAI error"):
                ai_consumer.process_message(message)

            # Verify Kafka publish was NOT called
            ai_consumer.kafka_helper.publish.assert_not_called()

    def test_process_with_openai_success(self, ai_consumer):
        """Test successful OpenAI API call"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is the AI response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        ai_consumer.openai_client.chat.completions.create.return_value = mock_response

        result = ai_consumer.process_with_openai("Hello AI")

        assert result == "This is the AI response"

        # Verify OpenAI was called with correct parameters
        ai_consumer.openai_client.chat.completions.create.assert_called_once()
        call_kwargs = ai_consumer.openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert call_kwargs["messages"][1]["content"] == "Hello AI"
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["timeout"] == 2.0

    def test_process_with_openai_timeout(self, ai_consumer):
        """Test OpenAI API timeout"""
        ai_consumer.openai_client.chat.completions.create.side_effect = TimeoutError(
            "Request timeout"
        )

        with pytest.raises(TimeoutError):
            ai_consumer.process_with_openai("Hello")

    def test_process_with_openai_rate_limit(self, ai_consumer):
        """Test OpenAI API rate limit error"""
        ai_consumer.openai_client.chat.completions.create.side_effect = Exception(
            "rate_limit exceeded"
        )

        with pytest.raises(Exception, match="rate_limit"):
            ai_consumer.process_with_openai("Hello")

    def test_process_with_openai_generic_error(self, ai_consumer):
        """Test OpenAI API generic error"""
        ai_consumer.openai_client.chat.completions.create.side_effect = Exception(
            "API error"
        )

        with pytest.raises(Exception, match="API error"):
            ai_consumer.process_with_openai("Hello")

    def test_cleanup(self, ai_consumer):
        """Test cleanup method"""
        ai_consumer.cleanup()

        # Verify executor was shut down
        ai_consumer.executor.shutdown.assert_called_once_with(
            wait=True, cancel_futures=False
        )

        # Verify kafka was torn down
        ai_consumer.kafka_helper.teardown.assert_called_once()


class TestProcessMessageContent:
    """Test various message content scenarios"""

    @pytest.fixture
    def ai_consumer(self):
        """Create AIConsumer with minimal mocking"""
        with (
            patch("ai_consumer.dependencies.KafkaHelper"),
            patch("ai_consumer.dependencies.OpenAI"),
            patch("ai_consumer.dependencies.ThreadPoolExecutor"),
        ):
            consumer = AIConsumer()
            consumer.kafka_helper = MagicMock()
            consumer.openai_client = MagicMock()
            return consumer

    def test_empty_content(self, ai_consumer):
        """Test processing message with empty content"""
        with patch.object(
            ai_consumer, "process_with_openai", return_value="Response"
        ) as mock_openai:
            message = {
                "userid": "testuser",
                "content": "",
                "correlation_id": "test-123",
            }

            ai_consumer.process_message(message)

            # Should still call OpenAI with empty string
            mock_openai.assert_called_once_with("")

    def test_long_content(self, ai_consumer):
        """Test processing message with long content"""
        with patch.object(
            ai_consumer, "process_with_openai", return_value="Response"
        ) as mock_openai:
            long_text = "This is a very long message. " * 100
            message = {
                "userid": "testuser",
                "content": long_text,
                "correlation_id": "test-123",
            }

            ai_consumer.process_message(message)

            # Should call OpenAI with full content
            mock_openai.assert_called_once_with(long_text)

    def test_special_characters_content(self, ai_consumer):
        """Test processing message with special characters"""
        with patch.object(
            ai_consumer, "process_with_openai", return_value="Response"
        ) as mock_openai:
            special_text = "Hello! 你好 🎉 \n\t Special chars: @#$%^&*()"
            message = {
                "userid": "testuser",
                "content": special_text,
                "correlation_id": "test-123",
            }

            ai_consumer.process_message(message)

            # Should handle special characters
            mock_openai.assert_called_once_with(special_text)
