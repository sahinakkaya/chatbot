import json
import logging
import time
from functools import partial
from typing import Dict, Set

import metrics.websocket as metrics
from fastapi import WebSocket
from logger import correlation_id_var
from websocket_server.config import settings
from websocket_server.handlers.message_handler import (
    MessageHandler,
    MessageHandlerError,
)
from websocket_server.util import redis_helper

logger = logging.getLogger(__name__)

message_handler = MessageHandler()


class WebSocketHandler:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        logger.info(f"userid is {user_id}")
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            channel = f"user:{user_id}"
            message_handler = partial(self.broadcast, channel)
            await redis_helper.subscribe(channel, message_handler)

        self.active_connections[user_id].add(websocket)

        metrics.websocket_connections_total.labels(server_id=settings.server_id).inc()
        total_connections = sum(
            len(conns) for conns in self.active_connections.values()
        )
        metrics.websocket_connections_active.labels(server_id=settings.server_id).set(
            total_connections
        )

        logger.info(
            f"WebSocket connected: server_id={settings.server_id}, {user_id=} total_connections_of_user={len(self.active_connections[user_id])}"
        )

    async def receive_and_process_messages(self, websocket: WebSocket, userid: str):
        while True:
            start_time = time.time()
            data = await websocket.receive_json()

            try:
                await message_handler.process_message(data, userid)
            except MessageHandlerError as e:
                logger.warning(f"Message handler error for user {userid}: {str(e)}")
                await websocket.send_json({"message": str(e), "type": "error"})

            # Record message processing duration
            duration = time.time() - start_time
            metrics.websocket_message_duration_seconds.labels(
                server_id=settings.server_id
            ).observe(duration)

    async def disconnect(
        self, websocket: WebSocket, user_id: str, reason: str = "normal"
    ):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                channel = f"user:{user_id}"
                await redis_helper.unsubscribe(channel)
                logger.info(f"All connections closed for user_id={user_id}")

        metrics.websocket_disconnections_total.labels(
            server_id=settings.server_id, reason=reason
        ).inc()
        total_connections = sum(
            len(conns) for conns in self.active_connections.values()
        )
        metrics.websocket_connections_active.labels(server_id=settings.server_id).set(
            total_connections
        )

        logger.info(
            f"WebSocket disconnected: server_id={settings.server_id}, {user_id=} total_connections_of_user={len(self.active_connections.get(user_id, []))}"
        )

    async def broadcast(self, channel: str, message: dict):
        data = json.loads(message["data"])

        correlation_id_var.set(data["correlation_id"])
        logger.info(f"Broadcasting message to channel {channel}: {message}")
        user_id = channel.split(":")[1]

        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(data)
                metrics.websocket_messages_sent_total.labels(
                    server_id=settings.server_id, userid=user_id
                ).inc()
