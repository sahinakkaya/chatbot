from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from chatbot.ai_service import AIService
from chatbot.handlers.message_handler import MessageHandler, MessageHandlerError
from chatbot.handlers.websocket_handler import WebSocketHandler


async def response_stream():
    yield {"type": "response.delta", "content": "Hello"}
    yield {"type": "response.done", "content": "Hello"}


async def text_delta_stream():
    yield "Hello"


@pytest.mark.asyncio
async def test_message_handler_starts_ai_response_stream():
    ai_service = MagicMock()
    ai_service.stream_response.return_value = response_stream()
    handler = MessageHandler(ai_service)

    with patch("chatbot.handlers.message_handler.check_rate_limit", return_value=True):
        stream = await handler.start_stream(
            {"type": "message", "content": "Hi"}, "user-1"
        )

    assert [event async for event in stream] == [
        {"type": "response.delta", "content": "Hello"},
        {"type": "response.done", "content": "Hello"},
    ]
    ai_service.stream_response.assert_called_once()


@pytest.mark.asyncio
async def test_message_handler_rejects_rate_limited_user():
    handler = MessageHandler(MagicMock())

    with patch("chatbot.handlers.message_handler.check_rate_limit", return_value=False):
        with pytest.raises(MessageHandlerError, match="Rate limit exceeded"):
            await handler.start_stream({"type": "message", "content": "Hi"}, "user-1")


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


@pytest.mark.asyncio
async def test_websocket_handler_broadcasts_each_stream_event():
    message_handler = MagicMock()
    message_handler.start_stream = AsyncMock(return_value=response_stream())
    handler = WebSocketHandler(message_handler)
    connection = AsyncMock()
    connection.receive_json.side_effect = [
        {"type": "message", "content": "Hi"},
        WebSocketDisconnect(),
    ]

    await handler.connect(connection, "user-1")

    with pytest.raises(WebSocketDisconnect):
        await handler.receive_and_process_messages(connection, "user-1")

    assert connection.send_json.await_count == 2
    assert connection.send_json.await_args_list[0].args[0]["type"] == "response.delta"
    assert connection.send_json.await_args_list[1].args[0]["type"] == "response.done"


@pytest.mark.asyncio
async def test_ai_service_saves_history_after_stream_completion():
    service = AIService()
    service.stream_with_openai = MagicMock(return_value=text_delta_stream())
    service.update_conversation_history = AsyncMock()

    events = [
        event
        async for event in service.stream_response("user-1", "Hi", "correlation-1")
    ]

    assert [event["type"] for event in events] == [
        "response.delta",
        "response.done",
    ]
    assert events[-1]["content"] == "Hello"
    service.update_conversation_history.assert_awaited_once_with(
        "user-1", "Hi", "Hello"
    )
