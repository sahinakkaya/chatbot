import logging
import asyncio
import redis.asyncio as redis
import redis.asyncio.client as redis_client
from fastapi import WebSocket
import json
from typing import Dict, Set

from kafka import KafkaProducer
from websocket_server.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client: redis.Redis | None = None
        self.kafka_producer: KafkaProducer | None = None
        self.pubsub: redis_client.PubSub | None = None

    async def initialize(self):
        # TODO: add error handling and retries
        self.redis_client = await redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )

        self.pubsub = self.redis_client.pubsub()
        logger.info(f"Redis connected server_id={settings.server_id}")

        # TODO: add error handling and retries
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
            max_block_ms=5000,
        )

        logger.info(f"Kafka connected server_id={settings.server_id}")

    async def connect(self, websocket: WebSocket, user_id: str):
        assert self.pubsub is not None, "PubSub not initialized"
        logger.info(f"user is is {user_id}")
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            # Subscribe to user-specific Redis channel
            await self.pubsub.subscribe(f"user:{user_id}")
            logger.info(
                f"Subscribed to Redis channel server_id={settings.server_id}, user_id={user_id}",
            )

        self.active_connections[user_id].add(websocket)
        logger.info(
            f"WebSocket connected: server_id={settings.server_id}, {user_id=} total_connections_of_user={len(self.active_connections[user_id])}",
        )

    async def disconnect(self, websocket: WebSocket, user_id: str):
        assert self.pubsub is not None, "PubSub not initialized"

        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                # No more active connections for this user, unsubscribe from Redis channel
                await self.pubsub.unsubscribe(f"user:{user_id}")
                del self.active_connections[user_id]
                logger.info(
                    f"Unsubscribed from Redis channel server_id={settings.server_id}, user_id={user_id}",
                )
        logger.info(
            f"WebSocket disconnected: server_id={settings.server_id}, {user_id=} total_connections_of_user={len(self.active_connections.get(user_id, []))}",
        )

    def publish_to_kafka(self, topic: str, message: dict):
        """Publish message to Kafka topic"""
        assert self.kafka_producer is not None, "Kafka producer not initialized"

        try:
            self.kafka_producer.send(topic, message)
            self.kafka_producer.flush()
            logger.info(
                f"Published to Kafka {topic=} user_id={message.get('userid')}",
            )
        except Exception as e:
            logger.error(
                f"Kafka publish failed error={str(e)}",
                extra={"topic": topic, "error": str(e)},
            )

    async def redis_listener(self):
        """Listen for messages from Redis pub/sub"""
        assert self.pubsub is not None, "PubSub not initialized"
        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                logger.info(f"Listening to Redis messages...")
                logger.info(message)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    user_id = channel.split(":")[1] if ":" in channel else None

                    if user_id:
                        data = json.loads(message["data"])
                        await self.broadcast(user_id, data)
                        logger.info(
                            f"Relayed message from Redis",
                        )

                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(
                    f"Redis listener error {str(e)}",
                )
                await asyncio.sleep(1)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, user_id: str, data: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(data)


conn_manager = ConnectionManager()
