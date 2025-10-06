from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    consume_topic: str = "responses"
    produce_topic: str = ""

    # Metrics
    metrics_port: int = 8001  # Port for Prometheus metrics HTTP server

    # logging
    log_level: str = "INFO"
    app_name: str = "message-relay"
    log_folder: str = "/var/log"

settings = Settings()
