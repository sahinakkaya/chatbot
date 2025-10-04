"""Prometheus metrics for Message Relay"""
from prometheus_client import Counter, Histogram, Gauge

# Performance Goal: Process 100+ messages per second throughput
message_relay_messages_received_total = Counter(
    'message_relay_messages_received_total',
    'Total number of messages consumed from Kafka',
    ['topic']
)

message_relay_messages_processed_total = Counter(
    'message_relay_messages_processed_total',
    'Total number of messages successfully processed',
    ['status']  # success, failed
)

message_relay_messages_failed_total = Counter(
    'message_relay_messages_failed_total',
    'Total number of messages that failed processing',
    ['error_type']
)

# Redis pub/sub metrics - Message distribution
message_relay_redis_publish_total = Counter(
    'message_relay_redis_publish_total',
    'Total messages published to Redis channels',
    ['status']  # success, failed
)

message_relay_redis_publish_errors_total = Counter(
    'message_relay_redis_publish_errors_total',
    'Total Redis publish errors',
    ['error_type']
)

message_relay_redis_subscribers = Gauge(
    'message_relay_redis_subscribers',
    'Number of subscribers when publishing to Redis channel',
    ['channel']
)

# Latency tracking - End-to-end message delivery
message_relay_processing_duration_seconds = Histogram(
    'message_relay_processing_duration_seconds',
    'Time spent processing and relaying each message',
    ['status'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

message_relay_redis_publish_duration_seconds = Histogram(
    'message_relay_redis_publish_duration_seconds',
    'Time spent publishing to Redis',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

# Kafka consumer metrics
message_relay_kafka_lag = Gauge(
    'message_relay_kafka_lag',
    'Kafka consumer lag (messages behind)',
    ['topic', 'partition']
)

message_relay_kafka_errors_total = Counter(
    'message_relay_kafka_errors_total',
    'Total Kafka consumer errors',
    ['error_type']
)

# Message routing tracking
message_relay_messages_by_user = Counter(
    'message_relay_messages_by_user',
    'Total messages relayed per user',
    ['userid']
)

# Zero subscribers tracking (messages sent but no one listening)
message_relay_zero_subscribers_total = Counter(
    'message_relay_zero_subscribers_total',
    'Total messages published with zero Redis subscribers',
    ['channel']
)
