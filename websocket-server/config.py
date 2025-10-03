from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    server_id: str = "server_1"


    log_level: str = "INFO"
    app_name: str = "websocket-server"
    log_folder: str = "/var/log"

settings = Settings()
