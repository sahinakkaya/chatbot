import logging

from asgi_correlation_id import correlation_id
from pydantic import ValidationError

from chatbot.ai_service import AIService
from chatbot.schemas import WebSocketUserMessage
from chatbot.util import check_rate_limit

logger = logging.getLogger(__name__)


class MessageHandlerError(Exception):
    pass


class MessageHandler:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def start_stream(self, raw_data: dict, userid: str):
        try:
            data = WebSocketUserMessage(**raw_data)
        except ValidationError as error:
            logger.warning(f"Invalid message format from user {userid}: {error}")
            raise MessageHandlerError("Please keep your message between 1 and 100 characters.")

        if not await check_rate_limit(userid):
            logger.warning(f"Rate limit exceeded for user {userid}")
            raise MessageHandlerError("Rate limit exceeded. Please slow down.")

        return self.ai_service.stream_response(
            userid=userid,
            content=data.content,
            correlation_id=correlation_id.get() or "-",
        )
