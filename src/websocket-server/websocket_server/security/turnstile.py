import logging
from typing import Optional

import httpx
from websocket_server.config import settings

logger = logging.getLogger(__name__)


async def verify_turnstile(token: str, remote_ip: Optional[str] = None) -> bool:
    """
    Verify Cloudflare Turnstile token.

    Args:
        token: The Turnstile token from the client
        remote_ip: Optional client IP address for additional verification

    Returns:
        True if verification succeeds, False otherwise
    """
    if not settings.turnstile_secret_key:
        logger.warning(
            "Turnstile secret key not configured, skipping verification"
        )
        return True  # Allow in development if not configured

    verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    payload = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }

    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                verify_url,
                json=payload,
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"Turnstile verification request failed with status {response.status_code}"
                )
                return False

            data = response.json()

            if not data.get("success"):
                error_codes = data.get("error-codes", [])
                logger.warning(
                    f"Turnstile verification failed: {error_codes}"
                )
                return False

            logger.info("Turnstile verification successful")
            return True

    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")
        return False
    except Exception as e:
        logger.error(f"Turnstile verification error: {str(e)}")
        return False
