import logging
import time
from contextlib import asynccontextmanager

from logger import setup_logger
from fastapi import FastAPI
from websocket_server.dependencies import conn_manager as manager

from websocket_server.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger(settings)
    logger.warning(f"Starting the application at {time.time()}")

    """Initialize connections on startup"""
    await manager.initialize()
    # TODO: start listening redis pubsub
    yield
    logger.warning(f"Shutting down the application at {time.time()}")

    if manager.kafka_producer:
        manager.kafka_producer.close()

    if manager.redis_client:
        await manager.redis_client.aclose()
