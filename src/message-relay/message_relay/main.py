import asyncio
import logging

from logger import setup_logger
from message_relay.config import settings
from message_relay.dependencies import MessageRelayService


async def main():
    setup_logger(settings, use_asgi_correlation_id=False)
    logger = logging.getLogger(__name__)

    logger.warning("Message Relay Service initialized.")
    message_relay_service = MessageRelayService()
    await message_relay_service.start()


if __name__ == "__main__":
    asyncio.run(main())
