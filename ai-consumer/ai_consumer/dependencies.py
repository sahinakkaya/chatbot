import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import metrics.ai_consumer as metrics
from ai_consumer.config import settings
from kafka_helper import KafkaHelper
from logger import correlation_id_var
from openai import OpenAI
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

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

            # Update metrics
            metrics.ai_consumer_messages_processed_total.labels(status="success").inc()
            metrics.ai_consumer_processing_duration_seconds.labels(
                status="success"
            ).observe(processing_time)
            metrics.ai_consumer_kafka_publish_total.labels(
                topic=settings.produce_topic, status="success"
            ).inc()

            logger.info(f"Sent response: {response_message}")
        except Exception as e:
            processing_time = time.time() - start_time
            metrics.ai_consumer_messages_failed_total.labels(
                error_type=type(e).__name__
            ).inc()
            metrics.ai_consumer_messages_processed_total.labels(status="failed").inc()
            metrics.ai_consumer_processing_duration_seconds.labels(
                status="failed"
            ).observe(processing_time)
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
        before_sleep=lambda retry_state: metrics.ai_consumer_openai_retries_total.labels(
            attempt=str(retry_state.attempt_number)
        ).inc(),
    )
    def process_with_openai(self, content):
        model = "gpt-3.5-turbo"
        start_time = time.time()

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
            duration = time.time() - start_time

            # Update metrics
            metrics.ai_consumer_openai_requests_total.labels(
                model=model, status="success"
            ).inc()
            metrics.ai_consumer_openai_duration_seconds.labels(model=model).observe(
                duration
            )
            metrics.ai_consumer_openai_tokens_total.labels(
                model=model, type="prompt"
            ).inc(response.usage.prompt_tokens)
            metrics.ai_consumer_openai_tokens_total.labels(
                model=model, type="completion"
            ).inc(response.usage.completion_tokens)
            metrics.ai_consumer_openai_tokens_total.labels(
                model=model, type="total"
            ).inc(response.usage.total_tokens)

            logger.info(f"AI response: {ai_response}")
            return ai_response
        except TimeoutError as e:
            metrics.ai_consumer_openai_requests_total.labels(
                model=model, status="timeout"
            ).inc()
            metrics.ai_consumer_openai_errors_total.labels(error_type="timeout").inc()
            logger.error(f"OpenAI API timeout: {str(e)}", extra={"error": str(e)})
            raise
        except Exception as e:
            error_type = "rate_limit" if "rate_limit" in str(e).lower() else "api_error"
            metrics.ai_consumer_openai_requests_total.labels(
                model=model, status="error"
            ).inc()
            metrics.ai_consumer_openai_errors_total.labels(error_type=error_type).inc()
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

                # Update metrics
                metrics.ai_consumer_messages_received_total.labels(
                    topic=settings.consume_topic
                ).inc()

                # Update thread pool metrics
                metrics.ai_consumer_thread_pool_active.set(
                    len([t for t in self.executor._threads if t.is_alive()])
                )
                metrics.ai_consumer_thread_pool_queue_size.set(
                    self.executor._work_queue.qsize()
                )

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
