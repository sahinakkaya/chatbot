import logging
from typing import Dict, Set

from fastapi import WebSocket

from chatbot.handlers.message_handler import MessageHandler, MessageHandlerError

logger = logging.getLogger(__name__)


class WebSocketHandler:
    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)
        logger.info(
            f"WebSocket connected: {user_id=} total_connections_of_user={len(self.active_connections[user_id])}"
        )

    async def receive_and_process_messages(self, websocket: WebSocket, userid: str):
        while True:
            data = await websocket.receive_json()
            try:
                response_stream = await self.message_handler.start_stream(data, userid)
                async for response in response_stream:
                    await self.broadcast(userid, response)
            except MessageHandlerError as error:
                logger.warning(f"Message handler error for user {userid}: {error}")
                await websocket.send_json({"message": str(error), "type": "error"})
            except Exception as error:
                logger.exception(f"Failed to process message for user {userid}: {error}")
                await websocket.send_json(
                    {"message": "Unable to process your message. Please try again.", "type": "error"}
                )

    async def disconnect(
        self, websocket: WebSocket, user_id: str, reason: str = "normal"
    ):
        connections = self.active_connections.get(user_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: {user_id=} reason={reason}")

    async def broadcast(self, userid: str, message: dict):
        for connection in self.active_connections.get(userid, set()).copy():
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection, userid, reason="send_failed")
