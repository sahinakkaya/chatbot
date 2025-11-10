import logging

from ai_consumer.config import settings
from ai_consumer.dependencies import AIConsumer
from logger import setup_logger

async def main():
    setup_logger(settings, use_asgi_correlation_id=False)
    logger = logging.getLogger(__name__)

    logger.warning("AI Consumer module initialized.")
    consumer = AIConsumer()
    await consumer.consume()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
