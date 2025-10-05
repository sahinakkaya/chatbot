import logging
import secrets

import metrics.websocket as metrics
from fastapi import Query
from kafka_helper import KafkaHelper
from redis_helper import RedisHelper
from websocket_server.config import settings

logger = logging.getLogger(__name__)

redis_helper = RedisHelper(settings)
kafka_helper = KafkaHelper(settings)



async def valid_user_with_token(token: str = Query(...), userid: str = Query(...)):
    is_valid = await validate_token(token, userid)
    if not is_valid:
        logger.warning(f"Invalid token for userid={userid}")
        metrics.websocket_message_errors_total.labels(
            server_id=settings.server_id, error_type="invalid_token"
        ).inc()
        return
    return userid


async def validate_token(token: str, userid: str) -> bool:
    stored_userid = await redis_helper.get(f"token:{token}")
    return stored_userid == userid


async def generate_token(userid: str) -> str:
    token = secrets.token_urlsafe(32)
    await redis_helper.set(f"token:{token}", userid, settings.token_ttl)
    logger.info(f"Generated token for userid={userid}, ttl={settings.token_ttl}s")
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
