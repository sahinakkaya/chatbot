import logging
from datetime import datetime
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
    room = userid
    await conn_manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message" and data.get("content"):
                kafka_message = {
                    "type": "message",
                    "content": data["content"],
                    "userid": userid,
                    "timestamp": datetime.utcnow().isoformat(),
                    "server_id": settings.server_id,
                }
                conn_manager.publish_to_kafka("incoming_messages", kafka_message)
            else:
                logger.warning(f"Invalid message format from user {userid}: {data}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid message format",
                        "userid": userid,
                    }
                )
    except WebSocketDisconnect:
        await conn_manager.disconnect(websocket, room)
        await conn_manager.broadcast(room, {'message': f"User {userid} disconnected",})
    except Exception as e:
        logger.error(
            f"WebSocket error",
            extra={"userid": userid, "error": str(e), "server_id": settings.server_id},
        )
        await conn_manager.disconnect(websocket, userid)


@app.get("/")
async def root():
    logger.debug("debug something")
    logger.info("info something")
    logger.warning("warning something")
    logger.error("error something")
    logger.critical("critical something")
    return {"message": "Hello World from FastAPI"}
