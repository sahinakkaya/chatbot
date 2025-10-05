import logging
from datetime import datetime

import metrics.websocket as metrics
from asgi_correlation_id import correlation_id
from websocket_server.config import settings
from websocket_server.util import check_rate_limit, kafka_helper

logger = logging.getLogger(__name__)


class MessageHandler:
    async def check_rate_limit(self, userid: str) -> bool:
        """Check if user has exceeded rate limit"""
        is_allowed = await check_rate_limit(userid)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {userid}")
            metrics.websocket_message_errors_total.labels(
                server_id=settings.server_id, error_type="rate_limit"
            ).inc()
        return is_allowed

    async def process_message(self, data: dict, userid: str) -> dict | None:
        """Process incoming message and return error if any"""
        metrics.websocket_messages_received_total.labels(
            server_id=settings.server_id, userid=userid
        ).inc()

        if data.get("type") != "message" or not data.get("content"):
            logger.warning(f"Invalid message format from user {userid}: {data}")
            metrics.websocket_message_errors_total.labels(
                server_id=settings.server_id, error_type="invalid_format"
            ).inc()
            return {
                "type": "error",
                "message": "Invalid message format",
                "userid": userid,
            }

        # Check rate limit
        is_allowed = await self.check_rate_limit(userid)
        if not is_allowed:
            return {
                "type": "error",
                "message": "Rate limit exceeded. Please slow down.",
                "userid": userid,
            }

        # Publish to Kafka
        kafka_message = {
            "type": "message",
            "content": data["content"],
            "userid": userid,
            "timestamp": datetime.utcnow().isoformat(),
            "server_id": settings.server_id,
            "correlation_id": correlation_id.get(),
        }
        kafka_helper.publish(settings.produce_topic, kafka_message)
