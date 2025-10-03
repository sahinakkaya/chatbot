from kafka import KafkaConsumer
import json
import redis.asyncio as redis
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

    def start(self):
        """Consume messages from Kafka and relay them to Redis"""
        logger.info("Starting Message Relay Service")

        try:
            for message in self.consumer:
                logger.info(f"Received message: {message.value}")

        except KeyboardInterrupt:
            logger.info("Shutting down Message Relay Service")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            self.cleanup()

    def cleanup(self):
        if self.consumer:
            self.consumer.close()
        logger.info("Message Relay Service stopped")

