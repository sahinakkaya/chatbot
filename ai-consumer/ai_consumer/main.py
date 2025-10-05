import logging

from ai_consumer.config import settings
from ai_consumer.dependencies import AIConsumer
from logger import setup_logger
from prometheus_client import start_http_server

if __name__ == "__main__":
    setup_logger(settings, use_asgi_correlation_id=False)
    logger = logging.getLogger(__name__)

    # Start Prometheus metrics HTTP server
    logger.info(f"Starting Prometheus metrics server on port {settings.metrics_port}")
    start_http_server(settings.metrics_port)

    logger.warning("AI Consumer module initialized.")
    consumer = AIConsumer()
    consumer.consume()
