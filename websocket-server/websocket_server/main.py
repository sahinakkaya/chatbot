import logging
from fastapi import WebSocket, Query
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from websocket_server.config import settings
from websocket_server.dependencies import conn_manager
from asgi_correlation_id import CorrelationIdMiddleware

from websocket_server.middleware import lifespan

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


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(...), userid: str = Query(...)
):
    room = "user:" + userid
    await conn_manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await conn_manager.send_personal_message(f"You wrote: {data}", websocket)
            await conn_manager.broadcast(f"User {userid} says: {data}", room)
    except WebSocketDisconnect:
        await conn_manager.disconnect(websocket, room)
        await conn_manager.broadcast(f"User {userid} left the chat", room)


@app.get("/")
async def root():
    logger.debug("debug something")
    logger.info("info something")
    logger.warning("warning something")
    logger.error("error something")
    logger.critical("critical something")
    return {"message": "Hello World from FastAPI"}
