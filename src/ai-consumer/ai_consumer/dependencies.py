import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from ai_consumer.config import settings
from kafka_helper import KafkaHelper
from logger import correlation_id_var
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class AIConsumer:
    def __init__(self):
        self.kafka_helper = KafkaHelper(settings)
        self.kafka_helper.initialize(
            consumer_args={
                "group_id": "ai-consumer-group",
                "auto_offset_reset": "earliest",
                "enable_auto_commit": True,
            }
        )

        self.openai_client = OpenAI(api_key=settings.openai_api_key, max_retries=0)
        self.executor = ThreadPoolExecutor(max_workers=settings.max_workers)

        logger.info(
            f"AI Consumer initialized with {settings.max_workers} worker threads"
        )

    def process_message(self, message):
        """Process a single message with error handling"""
        userid = message.get("userid")
        content = message.get("content")
        start_time = time.time()

        correlation_id = message.get("correlation_id", "-")
        correlation_id_var.set(correlation_id)

        try:
            ai_response = self.process_with_openai(content)
            processing_time = time.time() - start_time

            response_message = {
                "type": "response",
                "content": ai_response,
                "userid": message.get("userid"),
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": int(processing_time * 1000),
                "correlation_id": correlation_id,
            }

            self.kafka_helper.publish(settings.produce_topic, response_message)

            logger.info(f"Sent response: {response_message}")
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Failed to process message: {str(e)}",
                extra={"userid": userid, "error": str(e)},
            )
            raise

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(7),
        wait=wait_exponential(),
        reraise=True,
    )
    def process_with_openai(self, content):
        model = "gpt-3.5-turbo"

        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Provide concise and friendly responses.",
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=500,
                temperature=0.7,
                timeout=2.0,  # 2 second timeout
            )
            ai_response = response.choices[0].message.content

            logger.info(f"AI response: {ai_response}")
            return ai_response
        except TimeoutError as e:
            logger.error(f"OpenAI API timeout: {str(e)}", extra={"error": str(e)})
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", extra={"error": str(e)})
            raise

    def consume(self):
        """Consume messages from Kafka and process them concurrently"""
        logger.info("Starting AI Consumer service with concurrent processing")

        assert self.kafka_helper.consumer is not None, "Kafka consumer not initialized"
        try:
            for message in self.kafka_helper.consumer:
                msg_correlation_id = message.value.get("correlation_id", "-")
                correlation_id_var.set(msg_correlation_id)

                logger.info(f"Received message: {message.value}")

                # Submit to thread pool for concurrent processing
                self.executor.submit(self.process_message, message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down AI Consumer")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            self.cleanup()

    def cleanup(self):
        if self.executor:
            logger.info("Waiting for worker threads to complete...")
            self.executor.shutdown(wait=True, cancel_futures=False)
        self.kafka_helper.teardown()
        logger.info("AI Consumer stopped")
