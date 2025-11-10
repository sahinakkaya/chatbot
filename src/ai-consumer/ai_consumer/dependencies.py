import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from ai_consumer.config import settings
from kafka_helper import KafkaHelper
from knowledge_base import KnowledgeBase
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

        # Initialize Redis for response caching
        self.redis_helper = RedisHelper(settings)
        logger.info("Redis helper initialized for caching")

        # Initialize Knowledge Base for RAG
        self.knowledge_base = None
        if settings.knowledge_base_path:
            kb_path = Path(settings.knowledge_base_path)
            if kb_path.exists():
                logger.info(f"Loading knowledge base from {settings.knowledge_base_path}")
                self.knowledge_base = KnowledgeBase(
                    data_path=settings.knowledge_base_path,
                    model_name="all-MiniLM-L6-v2",  # Small, fast model (~80MB)
                )
                logger.info("Knowledge base loaded successfully")
            else:
                logger.warning(
                    f"Knowledge base file not found: {settings.knowledge_base_path}"
                )
        else:
            logger.warning("No knowledge base path configured")

        logger.info(
            f"AI Consumer initialized with {settings.max_workers} worker threads"
        )

    def _get_cache_key(self, content: str) -> str:
        """Generate cache key for a question"""
        # Use hash to keep keys short and consistent
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"ai_response:{content_hash}"

    async def _get_cached_response(self, content: str) -> str | None:
        """Get cached response if available"""
        cache_key = self._get_cache_key(content)
        cached = await self.redis_helper.get(cache_key)
        if cached:
            logger.info(f"Cache hit for question: {content[:50]}...")
        return cached

    async def _cache_response(self, content: str, response: str) -> None:
        """Cache AI response for future use"""
        cache_key = self._get_cache_key(content)
        # Cache for 24 hours (86400 seconds)
        await self.redis_helper.set(cache_key, response, ttl=86400)
        logger.debug(f"Cached response for: {content[:50]}...")

    def process_message(self, message):
        """Process a single message with error handling"""
        userid = message.get("userid")
        content = message.get("content")
        start_time = time.time()

        correlation_id = message.get("correlation_id", "-")
        correlation_id_var.set(correlation_id)

        try:
            # Check cache first (synchronous - using Redis client directly)
            cached_response = None
            if self.redis_helper.redis_client and settings.enable_caching:
                cache_key = self._get_cache_key(content)
                cached_response = self.redis_helper.redis_client.get(cache_key)
                if cached_response:
                    logger.info(f"Cache hit for question: {content[:50]}...")
                    ai_response = cached_response
                    processing_time = time.time() - start_time

                    response_message = {
                        "type": "response",
                        "content": ai_response,
                        "userid": message.get("userid"),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "processing_time_ms": int(processing_time * 1000),
                        "correlation_id": correlation_id,
                        "cached": True,
                    }

                    self.kafka_helper.publish(settings.produce_topic, response_message)
                    logger.info(f"Sent cached response: {response_message}")
                    return

            # Process with OpenAI (with RAG if available)
            ai_response = self.process_with_openai(content)
            processing_time = time.time() - start_time

            # Cache the response
            if self.redis_helper.redis_client and settings.enable_caching:
                cache_key = self._get_cache_key(content)
                self.redis_helper.redis_client.setex(
                    cache_key, settings.cache_ttl_seconds, ai_response
                )
                logger.debug(f"Cached response for: {content[:50]}...")

            response_message = {
                "type": "response",
                "content": ai_response,
                "userid": message.get("userid"),
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": int(processing_time * 1000),
                "correlation_id": correlation_id,
                "cached": False,
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

    def _build_system_prompt(self, context: str = "") -> str:
        """Build system prompt with optional context from knowledge base"""
        base_prompt = settings.system_prompt_template

        if context and self.knowledge_base:
            # Add context to system prompt
            return f"""{base_prompt}

Use the following information to answer questions. Only answer based on this context. If the information is not in the context, politely say that you don't have that information.

Context:
{context}

Remember: Be concise, friendly, and only answer based on the provided context."""
        else:
            return base_prompt

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(7),
        wait=wait_exponential(),
        reraise=True,
    )
    def process_with_openai(self, content):
        model = "gpt-3.5-turbo"

        # Get context from knowledge base if available
        context = ""
        confidence = 0.0

        if self.knowledge_base:
            try:
                context, confidence = self.knowledge_base.get_context_for_query(
                    content,
                    max_chunks=settings.rag_max_chunks,
                    threshold=settings.rag_confidence_threshold,
                )
                if context:
                    logger.info(
                        f"Retrieved context from knowledge base (confidence: {confidence:.2f})"
                    )
                else:
                    logger.info("No relevant context found in knowledge base")
            except Exception as e:
                logger.error(f"Error querying knowledge base: {str(e)}")
                # Continue without context

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                max_tokens=settings.max_tokens_per_response,
                temperature=0.7,
                timeout=2.0,  # 2 second timeout
            )
            ai_response = response.choices[0].message.content

            # Log token usage for cost tracking
            if hasattr(response, "usage"):
                logger.info(
                    f"Token usage: {response.usage.prompt_tokens} prompt + "
                    f"{response.usage.completion_tokens} completion = "
                    f"{response.usage.total_tokens} total"
                )

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
