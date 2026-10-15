from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatbot.handlers.message_handler import MessageHandler, MessageHandlerError
from chatbot.handlers.websocket_handler import WebSocketHandler


@pytest.mark.asyncio
async def test_message_handler_returns_direct_ai_response():
    ai_service = MagicMock()
    ai_service.create_response = AsyncMock(return_value={"type": "response", "content": "Hello"})
    handler = MessageHandler(ai_service)

    with patch("chatbot.handlers.message_handler.check_rate_limit", return_value=True):
        response = await handler.process_message(
            {"type": "message", "content": "Hi"}, "user-1"
        )

    assert response == {"type": "response", "content": "Hello"}
    ai_service.create_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_handler_rejects_rate_limited_user():
    handler = MessageHandler(MagicMock())

    with patch("chatbot.handlers.message_handler.check_rate_limit", return_value=False):
        with pytest.raises(MessageHandlerError, match="Rate limit exceeded"):
            await handler.process_message({"type": "message", "content": "Hi"}, "user-1")


@pytest.mark.asyncio
async def test_websocket_handler_broadcasts_direct_response_to_user_connections():
    message_handler = MagicMock()
    handler = WebSocketHandler(message_handler)
    first_connection = AsyncMock()
    second_connection = AsyncMock()

    await handler.connect(first_connection, "user-1")
    await handler.connect(second_connection, "user-1")
    await handler.broadcast("user-1", {"type": "response", "content": "Hello"})

    first_connection.send_json.assert_awaited_once()
    second_connection.send_json.assert_awaited_once()
