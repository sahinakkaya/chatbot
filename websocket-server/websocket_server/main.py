import logging

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from websocket_server.config import settings
from websocket_server.middleware import lifespan
from websocket_server.router import router

logger = logging.getLogger(__name__)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.allow_methods,
    allow_headers=settings.allow_headers,
)

app.add_middleware(CorrelationIdMiddleware)
app.include_router(router)
