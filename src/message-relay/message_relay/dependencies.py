import json
import logging

from kafka_helper import KafkaHelper
from logger import correlation_id_var
from message_relay.config import settings
from redis_helper import RedisHelper

logger = logging.getLogger(__name__)


class MessageRelayService:
    def __init__(self):
        self.kafka_helper = KafkaHelper(settings)
        self.kafka_helper.initialize(
            consumer_args={
                "group_id": "message-relay-group",
                "auto_offset_reset": "earliest",
            }
        )
        self.redis_helper = RedisHelper(settings)

    async def start(self):
        """Consume messages from Kafka and process them"""
        logger.info("Starting Message Relay Service")

        await self.redis_helper.initialize()

        assert self.kafka_helper.consumer is not None, (
            "Kafka consumer is not initialized"
        )
        try:
            for message in self.kafka_helper.consumer:
                msg_correlation_id = message.value.get("correlation_id", "-")
                correlation_id_var.set(msg_correlation_id)

                logger.info(f"Received message: {message.value}")


                await self.process_message(message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down Message Relay Service")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            await self.cleanup()

    async def process_message(self, message: dict):
        """Process message and relay to Redis"""

        try:
            user_id = message.get("userid")
            msg_type = message.get("type")

            if not user_id:
                logger.warning("Message missing userid", extra={"message": message})
                return

            logger.info(
                "Processing message from Kafka",
                extra={"userid": user_id, "type": msg_type},
            )

            # Publish to Redis for WebSocket distribution
            await self.publish_to_redis(user_id, message)

            logger.info(
                f"Message relayed successfully {user_id=} {msg_type=}",
                extra={"userid": user_id, "type": msg_type},
            )

        except Exception as e:
            logger.error(
                "Message processing failed",
                extra={"userid": message.get("userid"), "error": str(e)},
            )

    async def publish_to_redis(self, user_id: str, message: dict):
        """Publish message to user-specific Redis channel"""

        try:
            channel = f"user:{user_id}"
            if "type" not in message:
                message["type"] = "response"
            message_json = json.dumps(message)
            logger.info(message_json)

            subscribers = await self.redis_helper.publish(channel, message_json)

            logger.info(
                "Published to Redis",
                extra={
                    "channel": channel,
                    "userid": user_id,
                    "subscribers": subscribers,
                    "message_type": message.get("type"),
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to publish to Redis {str(e)}",
                extra={"userid": user_id, "error": str(e)},
            )
            raise

    async def cleanup(self):
        self.kafka_helper.teardown()
        await self.redis_helper.teardown()
        logger.info("Message Relay Service stopped")
