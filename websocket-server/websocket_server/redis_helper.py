import logging
import asyncio
import redis.asyncio as redis
import redis.asyncio.client as redis_client
import json
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class RedisHelper:
    def __init__(self, settings):
        self.redis_client: redis.Redis | None = None
        self.pubsub: redis_client.PubSub | None = None
        self.settings = settings

    async def initialize(self):
        self.redis_client = await redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            decode_responses=True,
        )
        self.pubsub = self.redis_client.pubsub()
        logger.info(f"Redis initialized for {self.settings.app_name}")

    async def subscribe(self, channel: str, message_handler):
        if self.pubsub is None:
            raise RuntimeError("PubSub not initialized")
        await self.pubsub.subscribe(**{channel: message_handler})

    async def unsubscribe(self, user_id: str):
        if self.pubsub is None:
            raise RuntimeError("PubSub not initialized")
        await self.pubsub.unsubscribe(f"user:{user_id}")
        logger.info(
            f"Unsubscribed from Redis channel server_id={self.settings.server_id}, user_id={user_id}"
        )

    async def listen_and_broadcast(
        self, message_handler: Callable[[str, dict], Awaitable[None]]
    ):
        if self.pubsub is None:
            raise RuntimeError("PubSub not initialized")

        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                if message and message["type"] in ("message", "pmessage"):
                    channel = message.get("channel") or message.get("pattern") or ""
                    user_id = channel.split(":")[1] if ":" in channel else None

                    if user_id:
                        data = json.loads(message["data"])
                        await message_handler(user_id, data)
                        logger.info(f"Relayed message from Redis to {user_id}")

                await asyncio.sleep(0.01)
            except Exception as e:
                if "pubsub connection not set" not in str(e):
                    logger.error(f"Redis listener error {str(e)}")
                await asyncio.sleep(1)

    async def teardown(self):
        if self.pubsub:
            await self.pubsub.close()
            logger.info(f"Redis pubsub closed for {self.settings.app_name}")
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info(f"Redis client closed for {self.settings.app_name}")
