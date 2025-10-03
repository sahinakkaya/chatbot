from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""


    # redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    incoming_topic: str = "incoming_messages"
    responses_topic: str = "responses"


    # logging
    log_level: str = "INFO"
    app_name: str = "ai-consumer"
    log_folder: str = "/var/log"

settings = Settings()
