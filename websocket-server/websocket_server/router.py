from fastapi import WebSocket, Query, Response, APIRouter, WebSocketDisconnect
from datetime import datetime
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging
import metrics.websocket as metrics
from websocket_server.config import settings
from asgi_correlation_id import correlation_id

from websocket_server.dependencies import conn_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(...), userid: str = Query(...)
):
    # Validate token before accepting connection
    is_valid = await conn_manager.validate_token(token, userid)
    if not is_valid:
        await websocket.close(code=1008, reason="Invalid token")
        logger.warning(f"Invalid token for userid={userid}")
        metrics.websocket_message_errors_total.labels(
            server_id=settings.server_id, error_type="invalid_token"
        ).inc()
        return

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
                # Check rate limit
                is_allowed = await conn_manager.check_rate_limit(userid)
                if not is_allowed:
                    logger.warning(f"Rate limit exceeded for user {userid}")
                    metrics.websocket_message_errors_total.labels(
                        server_id=settings.server_id, error_type="rate_limit"
                    ).inc()
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Rate limit exceeded. Please slow down.",
                            "userid": userid,
                        }
                    )
                    continue

                kafka_message = {
                    "type": "message",
                    "content": data["content"],
                    "userid": userid,
                    "timestamp": datetime.utcnow().isoformat(),
                    "server_id": settings.server_id,
                    "correlation_id": correlation_id.get(),
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
        await conn_manager.disconnect(websocket, room, reason="client_disconnect")
    except Exception as e:
        logger.error(
            f"WebSocket error",
            extra={"userid": userid, "error": str(e), "server_id": settings.server_id},
        )
        metrics.websocket_message_errors_total.labels(
            server_id=settings.server_id, error_type="exception"
        ).inc()
        await conn_manager.disconnect(websocket, userid, reason="error")


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancer"""
    return {
        "status": "healthy",
        "service": "websocket-server",
        "server_id": settings.server_id,
        "active_users": len(conn_manager.ws_manager.active_connections),
        "total_connections": sum(
            len(conns) for conns in conn_manager.ws_manager.active_connections.values()
        ),
    }


@router.get("/")
async def root():
    return {"message": "WebSocket Server", "server_id": settings.server_id}


@router.post("/token")
async def generate_token(userid: str = Query(...)):
    """Generate authentication token for user"""
    token = await conn_manager.generate_token(userid)
    return {"token": token, "userid": userid, "expires_in": 3600}


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
