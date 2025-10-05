import logging
import asyncio
from logger import setup_logger
from message_relay.config import settings
from message_relay.dependencies import MessageRelayService
from prometheus_client import start_http_server

async def main():
    setup_logger(settings, use_asgi_correlation_id=False)
    logger = logging.getLogger(__name__)

    # Start Prometheus metrics HTTP server
    logger.info(f"Starting Prometheus metrics server on port {settings.metrics_port}")
    start_http_server(settings.metrics_port)

    logger.warning("Message Relay Service initialized.")
    message_relay_service = MessageRelayService()
    await message_relay_service.start()


if __name__ == "__main__":
    asyncio.run(main())
