import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from ai_consumer.config import settings
from ai_consumer.rag_helper import RAGHelper
from kafka_helper import KafkaHelper
from logger import correlation_id_var
from openai import OpenAI
from redis_helper import RedisHelper
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Thread-local storage for event loops
_thread_local = threading.local()


def get_event_loop():
    """Get or create an event loop for the current thread"""
    try:
        loop = _thread_local.loop
        if loop.is_closed():
            raise AttributeError
    except AttributeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop
    return loop


def run_async(coro):
    """Run an async coroutine in the thread's event loop"""
    loop = get_event_loop()
    return loop.run_until_complete(coro)


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

        # Initialize RAG system
        self.rag_helper = RAGHelper(
            model_name=settings.rag_model_name,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        self.rag_helper.initialize_from_file(settings.context_file_path)

        self.openai_client = OpenAI(api_key=settings.openai_api_key, max_retries=0)
        self.executor = ThreadPoolExecutor(max_workers=settings.max_workers)

        # Initialize Redis helper for chat history
        self.redis_helper = RedisHelper(settings)

        logger.info(
            f"AI Consumer initialized with {settings.max_workers} worker threads, RAG system, and Redis chat history"
        )

    async def get_conversation_history(self, userid: str) -> list[dict]:
        """Retrieve conversation history for a user from Redis"""
        try:
            history_key = f"chat_history:{userid}"
            history_json = await self.redis_helper.get(history_key)

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

    async def update_conversation_history(
        self, userid: str, user_message: str, ai_response: str
    ):
        """Update conversation history in Redis with new message exchange"""
        try:
            history_key = f"chat_history:{userid}"

            # Get existing history
            history = await self.get_conversation_history(userid)

            # Add new messages
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": ai_response})

            # Trim history to max_messages (keep only the most recent messages)
            max_messages = settings.chat_history_max_messages
            if len(history) > max_messages:
                # Keep the most recent messages
                history = history[-max_messages:]

            # Store updated history with TTL
            await self.redis_helper.set(
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

    def process_message_sync(self, message):
        """Sync wrapper for async process_message - used by ThreadPoolExecutor"""
        run_async(self.process_message(message))

    async def process_message(self, message):
        """Process a single message with error handling"""
        userid = message.get("userid")
        content = message.get("content")
        start_time = time.time()

        correlation_id = message.get("correlation_id", "-")
        correlation_id_var.set(correlation_id)

        try:
            ai_response = await self.process_with_openai(userid, content)
            processing_time = time.time() - start_time

            # Update conversation history after successful response
            # await self.update_conversation_history(userid, content, ai_response)

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
    async def process_with_openai(self, userid: str, content: str):
        model = "gpt-3.5-turbo"

        try:
            # Get conversation history for the user
            # history = await self.get_conversation_history(userid)
            history = []

            # Retrieve relevant context chunks using RAG
            relevant_chunks = self.rag_helper.retrieve_relevant_chunks(
                query=content,
                top_k=settings.rag_top_k,
                min_similarity=settings.rag_min_similarity,
            )

            # Build system prompt with relevant context
            if relevant_chunks:
                context_text = "\n\n".join(relevant_chunks)
                system_content = f"""{settings.system_prompt}

Use the following information to answer questions if you need. It is written by Şahin Akkaya himself.

Context:
{context_text}
"""
            else:
                system_content = settings.system_prompt

            # Build messages array with system message, history, and new user message
            messages = [{"role": "system", "content": system_content}]

            # Add conversation history
            messages.extend(history)

            # Add current user message
            messages.append({"role": "user", "content": content})


            logger.debug(
                f"Sending to OpenAI with {len(history)} historical messages and {len(relevant_chunks)} context chunks for user {userid}"
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

    async def consume(self):
        """Consume messages from Kafka and process them concurrently"""
        logger.info("Starting AI Consumer service with concurrent processing")

        await self.redis_helper.initialize()

        assert self.kafka_helper.consumer is not None, "Kafka consumer not initialized"
        try:
            for message in self.kafka_helper.consumer:
                msg_correlation_id = message.value.get("correlation_id", "-")
                correlation_id_var.set(msg_correlation_id)

                logger.info(f"Received message: {message.value}")

                # Submit sync wrapper to thread pool for concurrent processing
                self.executor.submit(self.process_message_sync, message.value)

        except KeyboardInterrupt:
            logger.info("Shutting down AI Consumer")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", extra={"error": str(e)})
        finally:
            await self.cleanup()

    async def cleanup(self):
        if self.executor:
            logger.info("Waiting for worker threads to complete...")
            self.executor.shutdown(wait=True, cancel_futures=False)
        if self.redis_helper:
            await self.redis_helper.teardown()
            logger.info("Redis helper closed")
        self.kafka_helper.teardown()
        logger.info("AI Consumer stopped")
