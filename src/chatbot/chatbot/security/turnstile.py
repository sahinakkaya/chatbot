import logging

import httpx

from chatbot.config import settings

logger = logging.getLogger(__name__)


async def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    if not settings.turnstile_secret_key:
        logger.warning("Turnstile secret key not configured, skipping verification")
        return True

    payload = {"secret": settings.turnstile_secret_key, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                json=payload,
                timeout=10.0,
            )
        if response.status_code != 200:
            return False
        return response.json().get("success", False)
    except (httpx.TimeoutException, httpx.HTTPError) as error:
        logger.error(f"Turnstile verification error: {error}")
        return False
