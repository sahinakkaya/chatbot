from typing import Sequence
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    allow_origins: Sequence[str] = ["*"]
    allow_credentials: bool = False
    allow_methods: Sequence[str] = ["*"]
    allow_headers: Sequence[str] = ["*"]


    redis_host: str = "localhost"
    redis_port: int = 6379

    kafka_bootstrap_servers: str = "localhost:9092"
    produce_topic: str = ""
    consume_topic: str = ""
    server_id: str = "server_1"

    # logging
    log_level: str = "INFO"
    app_name: str = "websocket-server"
    log_folder: str = "/var/log"

    token_ttl: int = 3600
    user_rate_limit_max_requests: int = 10
    user_rate_limit_window_seconds: int = 60


settings = Settings()
