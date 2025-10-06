import logging

import redis.asyncio as redis
import redis.asyncio.client as redis_client

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

    async def unsubscribe(self, channel: str):
        if self.pubsub is None:
            raise RuntimeError("PubSub not initialized")
        await self.pubsub.unsubscribe(channel)
        logger.info(f"Unsubscribed from Redis channel channel={channel}")

    async def publish(self, channel: str, message: str):
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        await self.redis_client.publish(channel, message)

    async def get(self, key: str) -> str | None:
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        return await self.redis_client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        await self.redis_client.set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        return await self.redis_client.incr(key)

    async def teardown(self):
        if self.pubsub:
            await self.pubsub.aclose()
            logger.info(f"Redis pubsub closed for {self.settings.app_name}")
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info(f"Redis client closed for {self.settings.app_name}")
