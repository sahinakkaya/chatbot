"""
Rate limiting middleware using Redis to prevent abuse.

Implements multi-layer rate limiting:
- Per IP: 10 messages per minute
- Per user: 100 messages per hour
- Message size limit: 500 characters
- Connection limit per IP: 3 concurrent connections
"""

import logging
import time
from typing import Optional

from redis_helper import RedisHelper

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str, retry_after: int = 60):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class RateLimiter:
    """Redis-based rate limiter with multiple tiers"""

    def __init__(self, redis_helper: RedisHelper):
        self.redis = redis_helper

        # Rate limit configuration
        self.limits = {
            "messages_per_minute_per_ip": 10,
            "messages_per_hour_per_ip": 100,
            "max_message_length": 500,
            "max_connections_per_ip": 3,
        }

    def _get_redis_key(self, prefix: str, identifier: str, window: str) -> str:
        """Generate Redis key for rate limiting"""
        return f"ratelimit:{prefix}:{identifier}:{window}"

    def check_message_rate(self, ip: str, user_id: str) -> None:
        """
        Check if message rate limit is exceeded for given IP and user.

        Raises RateLimitExceeded if limit is exceeded.
        """
        current_time = int(time.time())

        # Check per-minute rate limit (per IP)
        minute_window = current_time // 60
        minute_key = self._get_redis_key("msg", ip, str(minute_window))

        if self.redis.client:
            minute_count = self.redis.client.get(minute_key)
            minute_count = int(minute_count) if minute_count else 0

            if minute_count >= self.limits["messages_per_minute_per_ip"]:
                retry_after = 60 - (current_time % 60)
                logger.warning(
                    f"Rate limit exceeded for IP {ip}: {minute_count} messages in current minute"
                )
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Maximum {self.limits['messages_per_minute_per_ip']} messages per minute. Try again in {retry_after} seconds.",
                    retry_after=retry_after,
                )

            # Increment counter and set expiry
            pipe = self.redis.client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # Keep for 2 minutes
            pipe.execute()

        # Check per-hour rate limit (per IP)
        hour_window = current_time // 3600
        hour_key = self._get_redis_key("msg_hour", ip, str(hour_window))

        if self.redis.client:
            hour_count = self.redis.client.get(hour_key)
            hour_count = int(hour_count) if hour_count else 0

            if hour_count >= self.limits["messages_per_hour_per_ip"]:
                retry_after = 3600 - (current_time % 3600)
                logger.warning(
                    f"Hourly rate limit exceeded for IP {ip}: {hour_count} messages in current hour"
                )
                raise RateLimitExceeded(
                    f"Hourly rate limit exceeded. Maximum {self.limits['messages_per_hour_per_ip']} messages per hour. Try again in {retry_after // 60} minutes.",
                    retry_after=retry_after,
                )

            # Increment counter and set expiry
            pipe = self.redis.client.pipeline()
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)  # Keep for 2 hours
            pipe.execute()

        logger.info(f"Rate check passed for IP {ip}, user {user_id}")

    def check_message_length(self, content: str) -> None:
        """
        Check if message length exceeds limit.

        Raises RateLimitExceeded if message is too long.
        """
        if len(content) > self.limits["max_message_length"]:
            raise RateLimitExceeded(
                f"Message too long. Maximum {self.limits['max_message_length']} characters allowed."
            )

    def check_connection_limit(self, ip: str, current_connections: int) -> None:
        """
        Check if connection limit is exceeded for given IP.

        Raises RateLimitExceeded if too many connections.
        """
        if current_connections >= self.limits["max_connections_per_ip"]:
            logger.warning(
                f"Connection limit exceeded for IP {ip}: {current_connections} connections"
            )
            raise RateLimitExceeded(
                f"Too many concurrent connections. Maximum {self.limits['max_connections_per_ip']} connections per IP allowed."
            )

    def validate_message(self, ip: str, user_id: str, content: str) -> None:
        """
        Validate message against all rate limits and constraints.

        This is the main entry point for rate limiting checks.
        """
        # Check message length first (no Redis needed)
        self.check_message_length(content)

        # Check rate limits
        self.check_message_rate(ip, user_id)

        logger.debug(f"Message validation passed for IP {ip}, user {user_id}")
