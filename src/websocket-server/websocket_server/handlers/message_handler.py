import logging

from asgi_correlation_id import correlation_id
from pydantic import ValidationError
from websocket_server.config import settings
from websocket_server.schemas import KafkaMessage, WebSocketUserMessage
from websocket_server.util import check_rate_limit, kafka_helper

logger = logging.getLogger(__name__)


class MessageHandlerError(Exception):
    pass


class MessageHandler:
    async def check_rate_limit(self, userid: str) -> bool:
        """Check if user has exceeded rate limit"""
        is_allowed = await check_rate_limit(userid)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {userid}")
        return is_allowed

    async def process_message(self, raw_data: dict, userid: str) -> dict | None:
        """Process incoming message and raise MessageHandlerError on failure"""
        try:
            data = WebSocketUserMessage(**raw_data)
        except ValidationError:
            logger.warning(f"Invalid message format from user {userid}: {raw_data}")
            raise MessageHandlerError("Invalid message format")

        # Check rate limit
        is_allowed = await self.check_rate_limit(userid)
        if not is_allowed:
            raise MessageHandlerError("Rate limit exceeded. Please slow down.")

        # Publish to Kafka
        kafka_message = KafkaMessage(
            **data.model_dump(),
            userid=userid,
            server_id=settings.server_id,
            correlation_id=correlation_id.get(),
        )
        kafka_helper.publish(settings.produce_topic, kafka_message.model_dump())
