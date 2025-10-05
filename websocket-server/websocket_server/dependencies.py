import logging
import redis.asyncio as redis
import redis.asyncio.client as redis_client
from fastapi import WebSocket
import json

from kafka import KafkaProducer
from websocket_server.config import settings
import metrics.websocket as metrics
from websocket_server.redis_helper import RedisHelper
from websocket_server.kafka_helper import KafkaHelper
from websocket_server.ws_connection_manager import WebSocketConnectionManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.ws_manager = WebSocketConnectionManager()
        self.redis_helper = RedisHelper(settings)
        self.kafka_helper = KafkaHelper(settings)
        self.pubsub: redis_client.PubSub | None = None

    async def initialize(self):
        # TODO: add error handling and retries
        await self.redis_helper.initialize()
        self.kafka_helper.initialize(producer_args={
            "retries":3,
            "max_block_ms":5000,
        })

    async def teardown(self):
        await self.redis_helper.teardown()
        self.kafka_helper.teardown()

    async def connect(self, websocket: WebSocket, user_id: str):
        is_first_connection = await self.ws_manager.connect(websocket, user_id)
        if is_first_connection:
            from functools import partial
            channel = f"user:{user_id}"
            message_handler = partial(self.ws_manager.broadcast, channel)
            await self.redis_helper.subscribe(channel, message_handler)

    async def disconnect(self, websocket: WebSocket, user_id: str, reason: str = 'normal'):
        was_last_connection = await self.ws_manager.disconnect(websocket, user_id, reason)
        if was_last_connection:
            await self.redis_helper.unsubscribe(user_id)


    def publish_to_kafka(self, topic: str, message: dict):
        self.kafka_helper.publish(topic, message)

conn_manager = ConnectionManager()
