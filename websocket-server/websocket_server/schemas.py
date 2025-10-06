from datetime import UTC, datetime
from pydantic import BaseModel, Field, field_validator
import re
from pydantic import BaseModel, Field
from typing import Literal


class UserId(BaseModel):
    userid: str = Field(
        description="User ID associated with the token",
        min_length=3,
        max_length=64,
    )

    @field_validator("userid")
    @classmethod
    def validate_userid(cls, v):
        # Only allow alphanumeric, dash, underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Invalid userid format")
        return v


class UrlParams(UserId):
    token: str = Field(
        description="Authentication token for the user", min_length=43, max_length=43
    )


class WebSocketUserMessage(BaseModel):
    type: Literal["message"] = Field(description="Message type")
    content: str = Field(min_length=1, max_length=400)
    timestamp: str = Field(
        description="ISO 8601 timestamp of the message",
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v):
        # Remove null bytes, control characters
        v = v.replace("\x00", "")
        # Strip excessive whitespace
        v = " ".join(v.split())
        return v

class KafkaMessage(WebSocketUserMessage):
    userid: str = Field(
        min_length=3,
        max_length=64,
    )
    server_id: str = ""
    correlation_id: str | None = ""
