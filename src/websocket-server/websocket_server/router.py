import logging
import time

from fastapi import APIRouter, Depends, Query, Response, WebSocket, WebSocketDisconnect
from websocket_server.config import settings
from websocket_server.handlers.websocket_handler import WebSocketHandler
from websocket_server.schemas import UserId
from websocket_server.util import (
    generate_token,
    get_valid_user_id,
    valid_user_with_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()
websocket_handler = WebSocketHandler()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, userid: str = Depends(valid_user_with_token)
):
    try:
        if not userid:
            raise WebSocketDisconnect(code=1008, reason="invalid_token")
        await websocket_handler.connect(websocket, userid)
        await websocket_handler.receive_and_process_messages(websocket, userid)

    except WebSocketDisconnect as e:
        if e.code == 1008:
            logger.info("WebSocket disconnected due to invalid token for user")
            await websocket.close(code=1008)
        else:
            await websocket_handler.disconnect(
                websocket, userid, reason="client_disconnected"
            )
    except Exception as e:
        logger.error(
            f"WebSocket error {str(e)}",
            extra={"userid": userid, "error": str(e), "server_id": settings.server_id},
        )
        await websocket_handler.disconnect(websocket, userid, reason="error")


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancer"""
    return {
        "status": "healthy",
        "service": "websocket-server",
        "server_id": settings.server_id,
        "active_users": len(websocket_handler.active_connections),
        "total_connections": sum(
            len(conns) for conns in websocket_handler.active_connections.values()
        ),
    }


@router.get("/")
async def root():
    return {"message": "WebSocket Server", "server_id": settings.server_id}


@router.post("/token")
async def generate_token_for_user(userid: UserId = Depends(get_valid_user_id)):
    """Generate authentication token for user"""
    token = await generate_token(userid.userid)
    return {"token": token, "userid": userid.userid, "expires_in": 3600}
