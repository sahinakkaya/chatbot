import logging

from asgi_correlation_id import correlation_id
from pydantic import ValidationError
from websocket_server.config import settings
from websocket_server.schemas import KafkaMessage, WebSocketUserMessage
from websocket_server.security import InputValidator, InputValidationError
from websocket_server.util import check_rate_limit, kafka_helper

logger = logging.getLogger(__name__)


class MessageHandlerError(Exception):
    pass


class MessageHandler:
    def __init__(self):
        self.input_validator = InputValidator()

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

        # Validate and sanitize input content
        try:
            sanitized_content = self.input_validator.validate_and_sanitize(
                data.content, max_length=settings.max_message_length
            )
            logger.debug(f"Input validated and sanitized for user {userid}")
        except InputValidationError as e:
            logger.warning(f"Input validation failed for user {userid}: {str(e)}")
            raise MessageHandlerError(str(e))

        # Check rate limit
        is_allowed = await self.check_rate_limit(userid)
        if not is_allowed:
            raise MessageHandlerError("Rate limit exceeded. Please slow down.")

        # Publish to Kafka with sanitized content
        kafka_message = KafkaMessage(
            type=data.type,
            content=sanitized_content,  # Use sanitized content
            userid=userid,
            server_id=settings.server_id,
            correlation_id=correlation_id.get(),
        )
        kafka_helper.publish(settings.produce_topic, kafka_message.model_dump())
