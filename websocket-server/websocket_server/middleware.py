import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from logger import setup_logger
from websocket_server.config import settings
from websocket_server.util import kafka_helper, redis_helper

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger(settings)
    logger.warning(f"Starting the application at {time.time()}")

    # Initialize connections
    # TODO: add error handling and retries
    await redis_helper.initialize()
    kafka_helper.initialize(
        producer_args={
            "retries": 3,
            "max_block_ms": 5000,
        }
    )


    # Start listening to Redis messages
    asyncio.create_task(redis_helper.pubsub.run())
    yield
    logger.warning(f"Shutting down the application at {time.time()}")

    await redis_helper.teardown()
    kafka_helper.teardown()

