import logging
from logger import setup_logger
from ai_consumer.config import settings

setup_logger(settings)
logger = logging.getLogger(__name__)

logger.warning("AI Consumer module initialized.")

def main():
    print("Hello from ai-consumer!")


if __name__ == "__main__":
    main()
