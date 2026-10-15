from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserId(BaseModel):
    userid: UUID = Field(description="User ID associated with the token")


class TokenRequest(BaseModel):
    captcha: str = Field(description="Cloudflare Turnstile token", min_length=1)


class UrlParams(BaseModel):
    userid: str = Field(description="User ID associated with the token")
    token: str = Field(
        description="Authentication token for the user", min_length=43, max_length=43
    )


class WebSocketUserMessage(BaseModel):
    type: Literal["message"] = Field(description="Message type")
    content: str = Field(min_length=1, max_length=100)
    timestamp: str = Field(
        description="ISO 8601 timestamp of the message",
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str):
        value = value.replace("\x00", "")
        return " ".join(value.split())
