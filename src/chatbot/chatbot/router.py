import logging

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from chatbot.handlers.message_handler import MessageHandler
from chatbot.handlers.websocket_handler import WebSocketHandler
from chatbot.middleware import ai_service
from chatbot.schemas import TokenRequest, UserId
from chatbot.security import verify_turnstile
from chatbot.util import generate_token, get_valid_user_id, valid_user_with_token

logger = logging.getLogger(__name__)

router = APIRouter()
websocket_handler = WebSocketHandler(MessageHandler(ai_service))


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, userid: str = Depends(valid_user_with_token)
):
    try:
        if not userid:
            raise WebSocketDisconnect(code=1008, reason="invalid_token")
        await websocket_handler.connect(websocket, userid)
        await websocket_handler.receive_and_process_messages(websocket, userid)
    except WebSocketDisconnect as error:
        if error.code == 1008:
            logger.info("WebSocket disconnected due to invalid token")
            await websocket.close(code=1008)
        else:
            await websocket_handler.disconnect(
                websocket, userid, reason="client_disconnected"
            )
    except Exception as error:
        logger.exception(f"WebSocket error for user {userid}: {error}")
        await websocket_handler.disconnect(websocket, userid, reason="error")


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "chatbot",
        "active_users": len(websocket_handler.active_connections),
        "total_connections": sum(
            len(connections) for connections in websocket_handler.active_connections.values()
        ),
    }


@router.get("/")
async def root():
    return {"message": "Real-time AI conversation chatbot"}


@router.post("/token")
async def generate_token_for_user(
    request: Request,
    token_request: TokenRequest,
    userid: UserId = Depends(get_valid_user_id),
):
    client_ip = request.client.host if request.client else None
    if not await verify_turnstile(token_request.captcha, client_ip):
        raise HTTPException(
            status_code=403,
            detail="Security verification failed. Please try again.",
        )

    token = await generate_token(str(userid.userid))
    logger.info(f"Token generated for userid={userid.userid}")
    return {"token": token, "userid": str(userid.userid), "expires_in": 3600}
