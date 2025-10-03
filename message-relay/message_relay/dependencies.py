from kafka import KafkaConsumer
import json
import redis
from message_relay.config import settings

import logging

logger = logging.getLogger(__name__)

class MessageRelayService:
    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.incoming_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            group_id='message-relay-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            max_poll_records=10
        )
        self.redis_client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )

    def start(self):
        """Consume messages from Kafka and process them"""
        logger.info("Starting Message Relay Service")

        try:
            for message in self.consumer:
                logger.info(f"Received message: {message.value}")
                self.process_message(message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down Message Relay Service")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            self.cleanup()

    def process_message(self, message: dict):
        """Process message and relay to Redis"""
        try:
            user_id = message.get('userid')
            msg_type = message.get('type')

            if not user_id:
                logger.warning("Message missing userid", extra={"message": message})
                return

            logger.info("Processing message from Kafka", extra={
                "userid": user_id,
                "type": msg_type
            })

            # Publish to Redis for WebSocket distribution
            self.publish_to_redis(user_id, message)

            logger.info(f"Message relayed successfully {user_id=} {msg_type=}", extra={
                "userid": user_id,
                "type": msg_type
            })

        except Exception as e:
            logger.error("Message processing failed", extra={
                "userid": message.get('userid'),
                "error": str(e)
            })

    def publish_to_redis(self, user_id: str, message: dict):
        """Publish message to user-specific Redis channel"""
        try:
            channel = f"user:{user_id}"
            message["type"] = "response"
            message_json = json.dumps(message)

            # Publish to Redis pub/sub
            subscribers = self.redis_client.publish(channel, message_json)

            logger.info("Published to Redis", extra={
                "channel": channel,
                "userid": user_id,
                "subscribers": subscribers,
                "message_type": message.get('type')
            })


        except Exception as e:
            logger.error("Failed to publish to Redis", extra={
                "userid": user_id,
                "error": str(e)
            })
            raise

    def cleanup(self):
        if self.consumer:
            self.consumer.close()

        if self.redis_client:
            self.redis_client.close()
        logger.info("Message Relay Service stopped")

