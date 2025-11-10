import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import redis
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

        # Initialize Redis client for chat history
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )

        logger.info(
            f"AI Consumer initialized with {settings.max_workers} worker threads and Redis chat history"
        )

    def get_conversation_history(self, userid: str) -> list[dict]:
        """Retrieve conversation history for a user from Redis"""
        try:
            history_key = f"chat_history:{userid}"
            history_json = self.redis_client.get(history_key)

            if history_json:
                history = json.loads(history_json)
                logger.debug(
                    f"Retrieved conversation history for user {userid}: {len(history)} messages"
                )
                return history
            else:
                logger.debug(f"No conversation history found for user {userid}")
                return []
        except Exception as e:
            logger.error(
                f"Failed to retrieve conversation history for user {userid}: {str(e)}"
            )
            return []

    def update_conversation_history(
        self, userid: str, user_message: str, ai_response: str
    ):
        """Update conversation history in Redis with new message exchange"""
        try:
            history_key = f"chat_history:{userid}"

            # Get existing history
            history = self.get_conversation_history(userid)

            # Add new messages
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": ai_response})

            # Trim history to max_messages (keep only the most recent messages)
            # Keep pairs of user/assistant messages, so ensure even number
            max_messages = settings.chat_history_max_messages
            if len(history) > max_messages:
                # Keep the most recent messages
                history = history[-max_messages:]

            # Store updated history with TTL
            self.redis_client.set(
                history_key,
                json.dumps(history),
                ex=settings.chat_history_ttl,
            )

            logger.debug(
                f"Updated conversation history for user {userid}: {len(history)} messages"
            )
        except Exception as e:
            logger.error(
                f"Failed to update conversation history for user {userid}: {str(e)}"
            )

    def process_message(self, message):
        """Process a single message with error handling"""
        userid = message.get("userid")
        content = message.get("content")
        start_time = time.time()

        correlation_id = message.get("correlation_id", "-")
        correlation_id_var.set(correlation_id)

        try:
            ai_response = self.process_with_openai(userid, content)
            processing_time = time.time() - start_time

            # Update conversation history after successful response
            self.update_conversation_history(userid, content, ai_response)

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
    def process_with_openai(self, userid: str, content: str):
        model = "gpt-3.5-turbo"

        try:
            # Get conversation history for the user
            history = self.get_conversation_history(userid)

            # Build messages array with system message, history, and new user message
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Provide concise and friendly responses.",
                }
            ]

            # Add conversation history
            messages.extend(history)

            # Add current user message
            messages.append({"role": "user", "content": content})

            logger.debug(
                f"Sending to OpenAI with {len(history)} historical messages for user {userid}"
            )

            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
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
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis client closed")
        self.kafka_helper.teardown()
        logger.info("AI Consumer stopped")
