import logging
from datetime import datetime
from fastapi import WebSocket, Query, Response
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from websocket_server.config import settings
from websocket_server.dependencies import conn_manager
from asgi_correlation_id import CorrelationIdMiddleware
import metrics.websocket as metrics
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

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
            start_time = time.time()
            data = await websocket.receive_json()

            metrics.websocket_messages_received_total.labels(
                server_id=settings.server_id, userid=userid
            ).inc()

            if data.get("type") == "message" and data.get("content"):
                kafka_message = {
                    "type": "message",
                    "content": data["content"],
                    "userid": userid,
                    "timestamp": datetime.utcnow().isoformat(),
                    "server_id": settings.server_id,
                }
                conn_manager.publish_to_kafka("incoming_messages", kafka_message)
                # await websocket.send_json({"type": "response", "content": data["content"]})
                # Record message processing duration
                duration = time.time() - start_time
                metrics.websocket_message_duration_seconds.labels(
                    server_id=settings.server_id
                ).observe(duration)
            else:
                logger.warning(f"Invalid message format from user {userid}: {data}")
                metrics.websocket_message_errors_total.labels(
                    server_id=settings.server_id, error_type="invalid_format"
                ).inc()
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid message format",
                        "userid": userid,
                    }
                )
    except WebSocketDisconnect:
        await conn_manager.disconnect(websocket, room, reason='client_disconnect')
    except Exception as e:
        logger.error(
            f"WebSocket error",
            extra={"userid": userid, "error": str(e), "server_id": settings.server_id},
        )
        metrics.websocket_message_errors_total.labels(
            server_id=settings.server_id, error_type="exception"
        ).inc()
        await conn_manager.disconnect(websocket, userid, reason='error')


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancer"""
    return {
        "status": "healthy",
        "service": "websocket-server",
        "server_id": settings.server_id,
        "active_users": len(conn_manager.active_connections),
        "total_connections": sum(len(conns) for conns in conn_manager.active_connections.values())
    }

@app.get("/")
async def root():
    return {"message": "WebSocket Server", "server_id": settings.server_id}

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
