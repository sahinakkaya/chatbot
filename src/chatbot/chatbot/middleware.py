import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from logger import setup_logger

from chatbot.ai_service import AIService
from chatbot.config import settings
from chatbot.util import redis_helper

logger = logging.getLogger(__name__)
ai_service = AIService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logger(settings)
    logger.warning(f"Starting the application at {time.time()}")
    await redis_helper.initialize()
    await asyncio.to_thread(ai_service.initialize)
    yield
    logger.warning(f"Shutting down the application at {time.time()}")
    await ai_service.teardown()
    await redis_helper.teardown()
