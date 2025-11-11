import logging
import secrets
from uuid import UUID

from fastapi import Depends, Query
from kafka_helper import KafkaHelper
from redis_helper import RedisHelper
from websocket_server.config import settings
from websocket_server.schemas import UrlParams, UserId

logger = logging.getLogger(__name__)

redis_helper = RedisHelper(settings)
kafka_helper = KafkaHelper(settings)


def get_valid_user_id(userid: UUID = Query(...)):
    return UserId(userid=userid)


def get_url_params(token: str = Query(...), userid: UUID = Query(...)):
    return UrlParams(token=token, userid=str(userid))


async def valid_user_with_token(params: UrlParams = Depends(get_url_params)):
    is_valid = await validate_token(params.token, params.userid)
    if not is_valid:
        logger.warning(f"Invalid token for userid={params.userid}")
        return
    return params.userid


async def validate_token(token: str, userid: str) -> bool:
    stored_token = await redis_helper.get(f"token:{userid}")
    return stored_token == token


async def generate_token(userid: str) -> str:
    """
    Generate or return existing authentication token for user.
    Stores as token:{userid} = token for easy lookup.
    """
    # Check if user already has a valid token
    existing_token = await redis_helper.get(f"token:{userid}")
    if existing_token:
        logger.info(f"Returning existing token for userid={userid}")
        return existing_token

    # Generate new token
    token = secrets.token_urlsafe(32)
    await redis_helper.set(f"token:{userid}", token, settings.token_ttl)
    logger.info(f"Generated new token for userid={userid}, ttl={settings.token_ttl}s")
    return token


async def check_rate_limit(userid: str) -> bool:
    key = f"rate_limit:{userid}"
    current = await redis_helper.get(key)

    if current is None:
        await redis_helper.set(key, "1", settings.user_rate_limit_window_seconds)
        return True

    count = int(current)
    if count >= settings.user_rate_limit_max_requests:
        return False

    await redis_helper.incr(key)
    return True
