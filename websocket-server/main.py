import logging
from fastapi import WebSocket, Query
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dependencies import conn_manager
from asgi_correlation_id import CorrelationIdMiddleware

from middleware import lifespan

logger = logging.getLogger(__name__)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CorrelationIdMiddleware)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(...), userid: str = Query(...)
):
    room = f"room_{token}"
    await conn_manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            await conn_manager.send_personal_message(f"You wrote: {data}", websocket)
            await conn_manager.broadcast(f"User {userid} says: {data}", room)
    except WebSocketDisconnect:
        conn_manager.disconnect(websocket, room)
        await conn_manager.broadcast(f"User {userid} left the chat", room)


@app.get("/")
async def root():
    logger.debug("debug something")
    logger.info("info something")
    logger.warning("warning something")
    logger.error("error something")
    logger.critical("critical something")
    return {"message": "Hello World from FastAPI"}
