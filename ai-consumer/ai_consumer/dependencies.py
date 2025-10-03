from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
import json
from openai import OpenAI
from ai_consumer.config import settings

import logging

logger = logging.getLogger(__name__)

class AIConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.incoming_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            group_id='ai-consumer-group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            max_poll_records=10
        )

        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )

        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info("AI Consumer initialized")

    def process_message(self, message):
        content = message.get('content')
        ai_response = f"AI response to message: {content}"
        response_message = {
            'type': 'response',
            'content': ai_response,
            'userid': message.get('userid'),
            'timestamp': datetime.utcnow().isoformat(),
        }
        self.producer.send(settings.responses_topic, value=response_message)
        logger.info(f"Sent response: {response_message}")


    def consume(self):
        """Consume messages from Kafka and process them"""
        logger.info("Starting AI Consumer service")

        try:
            for message in self.consumer:
                logger.info(f"Received message: {message.value}")
                self.process_message(message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down AI Consumer")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            self.cleanup()

    def cleanup(self):
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        logger.info("AI Consumer stopped")

