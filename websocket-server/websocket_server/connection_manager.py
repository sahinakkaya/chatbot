import logging
import json
from fastapi import WebSocket
from typing import Dict, Set
from websocket_server.config import settings
import metrics.websocket as metrics
from logger import correlation_id_var

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        logger.info(f"userid is {user_id}")
        await websocket.accept()

        is_first_connection = False
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            is_first_connection = True

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
        return is_first_connection

    async def disconnect(
        self, websocket: WebSocket, user_id: str, reason: str = "normal"
    ):
        is_last_connection = False
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                is_last_connection = True
                del self.active_connections[user_id]
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
        return is_last_connection

    async def broadcast(self, channel: str, message: dict):

        data = json.loads(message["data"])

        correlation_id_var.set(data['correlation_id'])
        logger.info(f"Broadcasting message to channel {channel}: {message}")
        user_id = channel.split(":")[1]

        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(data)
                metrics.websocket_messages_sent_total.labels(
                    server_id=settings.server_id, userid=user_id
                ).inc()
