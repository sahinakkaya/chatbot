import logging
import asyncio
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

    # Initialize connections
    await manager.initialize()


    # Start redis listener
    asyncio.create_task(manager.redis_listener())
    yield
    logger.warning(f"Shutting down the application at {time.time()}")
    await manager.teardown()

