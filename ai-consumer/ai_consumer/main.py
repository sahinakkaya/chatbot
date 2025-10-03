import logging
from logger import setup_logger
from ai_consumer.config import settings
from ai_consumer.dependencies import AIConsumer


if __name__ == "__main__":
    setup_logger(settings)
    logger = logging.getLogger(__name__)

    logger.warning("AI Consumer module initialized.")
    consumer = AIConsumer()
    consumer.consume()
