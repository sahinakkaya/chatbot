import logging
import time

import metrics.websocket as metrics
from fastapi import (APIRouter, Depends, Query, Response, WebSocket,
                     WebSocketDisconnect)
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from websocket_server.config import settings
from websocket_server.services.message_handler import MessageHandler
from websocket_server.services.websocket_manager import websocket_manager
from websocket_server.util import generate_token, valid_user_with_token

logger = logging.getLogger(__name__)

router = APIRouter()
message_handler = MessageHandler()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, userid: str = Depends(valid_user_with_token)
):
    try:
        if not userid:
            raise WebSocketDisconnect(code=1008, reason="invalid_token")
        await websocket_manager.connect(websocket, userid)
        while True:
            start_time = time.time()
            data = await websocket.receive_json()

            # Process message through service layer
            error_response = await message_handler.process_message(data, userid)

            if error_response:
                await websocket.send_json(error_response)
            else:
                # Record message processing duration
                duration = time.time() - start_time
                metrics.websocket_message_duration_seconds.labels(
                    server_id=settings.server_id
                ).observe(duration)

    except WebSocketDisconnect as e:
        if e.code == 1008:
            logger.info("WebSocket disconnected due to invalid token for user")
            await websocket.close(code=1008)
        else:
            await websocket_manager.disconnect(websocket, userid, reason="client_disconnected")
    except Exception as e:
        logger.error(
            f"WebSocket error {str(e)}",
            extra={"userid": userid, "error": str(e), "server_id": settings.server_id},
        )
        metrics.websocket_message_errors_total.labels(
            server_id=settings.server_id, error_type="exception"
        ).inc()
        await websocket_manager.disconnect(websocket, userid, reason="error")


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancer"""
    return {
        "status": "healthy",
        "service": "websocket-server",
        "server_id": settings.server_id,
        "active_users": len(websocket_manager.active_connections),
        "total_connections": sum(
            len(conns) for conns in websocket_manager.active_connections.values()
        ),
    }


@router.get("/")
async def root():
    return {"message": "WebSocket Server", "server_id": settings.server_id}


@router.post("/token")
async def generate_token_for_user(userid: str = Query(...)):
    """Generate authentication token for user"""
    token = await generate_token(userid)
    return {"token": token, "userid": userid, "expires_in": 3600}


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
