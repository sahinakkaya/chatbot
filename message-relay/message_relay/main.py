import logging
from logger import setup_logger
from message_relay.config import settings
from message_relay.dependencies import MessageRelayService

if __name__ == "__main__":
    setup_logger(settings)
    logger = logging.getLogger(__name__)

    logger.warning("Message Relay Service initialized.")
    message_relay_service = MessageRelayService()
    message_relay_service.start()

