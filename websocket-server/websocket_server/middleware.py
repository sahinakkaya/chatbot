import logging
import time
from contextlib import asynccontextmanager

from logger import setup_logger
from fastapi import FastAPI

from websocket_server.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger(settings)
    logger.warning(f"Starting the application at {time.time()}")
    yield
    logger.warning(f"Shutting down the application at {time.time()}")
