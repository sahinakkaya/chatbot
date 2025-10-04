from kafka import KafkaConsumer
import json
import redis
from message_relay.config import settings
import time
import metrics.message_relay as metrics

import logging

logger = logging.getLogger(__name__)

class MessageRelayService:
    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.incoming_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            group_id='message-relay-group',
            auto_offset_reset='earliest',
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

                # Update metrics
                metrics.message_relay_messages_received_total.labels(topic=settings.incoming_topic).inc()

                self.process_message(message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down Message Relay Service")
        except Exception as e:
            metrics.message_relay_kafka_errors_total.labels(error_type=type(e).__name__).inc()
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            self.cleanup()

    def process_message(self, message: dict):
        """Process message and relay to Redis"""
        start_time = time.time()

        try:
            user_id = message.get('userid')
            msg_type = message.get('type')

            if not user_id:
                logger.warning("Message missing userid", extra={"message": message})
                metrics.message_relay_messages_failed_total.labels(error_type="missing_userid").inc()
                return

            logger.info("Processing message from Kafka", extra={
                "userid": user_id,
                "type": msg_type
            })

            # Publish to Redis for WebSocket distribution
            self.publish_to_redis(user_id, message)

            # Update metrics
            processing_time = time.time() - start_time
            metrics.message_relay_messages_processed_total.labels(status="success").inc()
            metrics.message_relay_processing_duration_seconds.labels(status="success").observe(processing_time)
            metrics.message_relay_messages_by_user.labels(userid=user_id).inc()

            logger.info(f"Message relayed successfully {user_id=} {msg_type=}", extra={
                "userid": user_id,
                "type": msg_type
            })

        except Exception as e:
            processing_time = time.time() - start_time
            metrics.message_relay_messages_failed_total.labels(error_type=type(e).__name__).inc()
            metrics.message_relay_messages_processed_total.labels(status="failed").inc()
            metrics.message_relay_processing_duration_seconds.labels(status="failed").observe(processing_time)
            logger.error("Message processing failed", extra={
                "userid": message.get('userid'),
                "error": str(e)
            })

    def publish_to_redis(self, user_id: str, message: dict):
        """Publish message to user-specific Redis channel"""
        start_time = time.time()

        try:
            channel = f"user:{user_id}"
            if "type" not in message:
                message["type"] = "response"
            message_json = json.dumps(message)
            logger.info(message_json)

            # Publish to Redis pub/sub
            subscribers = self.redis_client.publish(channel, message_json)

            # Update metrics
            publish_time = time.time() - start_time
            metrics.message_relay_redis_publish_total.labels(status="success").inc()
            metrics.message_relay_redis_publish_duration_seconds.observe(publish_time)

            if subscribers == 0:
                metrics.message_relay_zero_subscribers_total.labels(channel=channel).inc()

            logger.info("Published to Redis", extra={
                "channel": channel,
                "userid": user_id,
                "subscribers": subscribers,
                "message_type": message.get('type')
            })

        except Exception as e:
            metrics.message_relay_redis_publish_total.labels(status="failed").inc()
            metrics.message_relay_redis_publish_errors_total.labels(error_type=type(e).__name__).inc()
            logger.error(f"Failed to publish to Redis {str(e)}", extra={
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

