"""Prometheus metrics for AI Consumer"""

from prometheus_client import Counter, Gauge, Histogram

# Performance Goal: Process 100+ messages per second
ai_consumer_messages_received_total = Counter(
    "ai_consumer_messages_received_total",
    "Total number of messages consumed from Kafka",
    ["topic"],
)

ai_consumer_messages_processed_total = Counter(
    "ai_consumer_messages_processed_total",
    "Total number of messages successfully processed",
    ["status"],  # success, failed
)

ai_consumer_messages_failed_total = Counter(
    "ai_consumer_messages_failed_total",
    "Total number of messages that failed processing",
    ["error_type"],
)

# OpenAI API metrics - Error Handling requirement
ai_consumer_openai_requests_total = Counter(
    "ai_consumer_openai_requests_total",
    "Total number of OpenAI API requests",
    ["model", "status"],  # status: success, timeout, error, retry
)

ai_consumer_openai_errors_total = Counter(
    "ai_consumer_openai_errors_total",
    "Total number of OpenAI API errors",
    ["error_type"],  # timeout, rate_limit, api_error
)

ai_consumer_openai_retries_total = Counter(
    "ai_consumer_openai_retries_total",
    "Total number of OpenAI API retry attempts",
    ["attempt"],  # 1, 2, 3
)

# Performance tracking - Message Throughput requirement
ai_consumer_processing_duration_seconds = Histogram(
    "ai_consumer_processing_duration_seconds",
    "Time spent processing each message (including OpenAI call)",
    ["status"],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
)

ai_consumer_openai_duration_seconds = Histogram(
    "ai_consumer_openai_duration_seconds",
    "Time spent on OpenAI API calls",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
)

# Kafka publishing metrics
ai_consumer_kafka_publish_total = Counter(
    "ai_consumer_kafka_publish_total",
    "Total messages published to Kafka responses topic",
    ["topic", "status"],
)

ai_consumer_kafka_publish_errors_total = Counter(
    "ai_consumer_kafka_publish_errors_total", "Total Kafka publish errors", ["topic"]
)

# Resource management - Thread pool tracking
ai_consumer_thread_pool_active = Gauge(
    "ai_consumer_thread_pool_active", "Number of active worker threads in the pool"
)

ai_consumer_thread_pool_queue_size = Gauge(
    "ai_consumer_thread_pool_queue_size", "Number of tasks waiting in thread pool queue"
)

# Token usage tracking
ai_consumer_openai_tokens_total = Counter(
    "ai_consumer_openai_tokens_total",
    "Total number of tokens used by OpenAI API",
    ["model", "type"],  # type: prompt, completion, total
)
