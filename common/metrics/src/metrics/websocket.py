"""Prometheus metrics for WebSocket Server"""
from prometheus_client import Counter, Gauge, Histogram

# Performance Goal: Support 100+ concurrent WebSocket connections
websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['server_id']
)

websocket_connections_total = Counter(
    'websocket_connections_total',
    'Total number of WebSocket connections established',
    ['server_id']
)

websocket_disconnections_total = Counter(
    'websocket_disconnections_total',
    'Total number of WebSocket disconnections',
    ['server_id', 'reason']
)

# Performance Goal: Process 100+ messages per second
websocket_messages_received_total = Counter(
    'websocket_messages_received_total',
    'Total number of messages received from clients',
    ['server_id', 'userid']
)

websocket_messages_sent_total = Counter(
    'websocket_messages_sent_total',
    'Total number of messages sent to clients',
    ['server_id', 'userid']
)

websocket_message_errors_total = Counter(
    'websocket_message_errors_total',
    'Total number of message processing errors',
    ['server_id', 'error_type']
)

# Message latency tracking
websocket_message_duration_seconds = Histogram(
    'websocket_message_duration_seconds',
    'Time spent processing WebSocket messages',
    ['server_id'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Kafka publishing metrics
websocket_kafka_publish_total = Counter(
    'websocket_kafka_publish_total',
    'Total messages published to Kafka',
    ['server_id', 'topic']
)

websocket_kafka_publish_errors_total = Counter(
    'websocket_kafka_publish_errors_total',
    'Total Kafka publish errors',
    ['server_id', 'topic']
)

# Redis subscription metrics
websocket_redis_messages_received_total = Counter(
    'websocket_redis_messages_received_total',
    'Total messages received from Redis pub/sub',
    ['server_id', 'channel']
)

websocket_redis_errors_total = Counter(
    'websocket_redis_errors_total',
    'Total Redis operation errors',
    ['server_id', 'operation']
)
