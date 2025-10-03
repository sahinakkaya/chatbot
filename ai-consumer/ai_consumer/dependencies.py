from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
import json
import time
from openai import OpenAI
from ai_consumer.config import settings

import logging

logger = logging.getLogger(__name__)


class AIConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.incoming_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="ai-consumer-group",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            max_poll_records=10,
        )

        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
        )

        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        logger.info("AI Consumer initialized")

    def process_message(self, message):
        content = message.get("content")

        start_time = time.time()
        ai_response = self.process_with_openai(content)
        processing_time = time.time() - start_time
        response_message = {
            "type": "response",
            "content": ai_response,
            "userid": message.get("userid"),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": int(processing_time * 1000),
        }
        self.producer.send(settings.responses_topic, value=response_message)
        logger.info(f"Sent response: {response_message}")

    def process_with_openai(self, content):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Provide concise and friendly responses.",
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            ai_response = response.choices[0].message.content
            logger.info(
                "OpenAI API call successful",
                extra={
                    "tokens_used": response.usage.total_tokens,
                    "model": response.model,
                },
            )
            logger.info(f"AI response: {ai_response}")

            return ai_response
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", extra={"error": str(e)})
            return "Error processing message with AI."

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
