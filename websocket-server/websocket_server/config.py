from typing import Sequence
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    allow_origins: Sequence[str] = ["*"]
    allow_credentials: bool = False
    allow_methods: Sequence[str] = ["*"]
    allow_headers: Sequence[str] = ["*"]

    kafka_bootstrap_servers: str = "localhost:9092"
    server_id: str = "server_1"

    log_level: str = "INFO"
    app_name: str = "websocket-server"
    log_folder: str = "/var/log"


settings = Settings()
