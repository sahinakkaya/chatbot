from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""

    # redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    consume_topic: str = "incoming_messages"
    produce_topic: str = "responses"

    # Concurrency
    max_workers: int = 50  # Number of concurrent OpenAI API calls

    # Chat History
    chat_history_max_messages: int = 20  # Maximum number of messages to keep in history, should be even number to keep pairs of user/assistant messages
    chat_history_ttl: int = 3600  # Time to live for chat history in seconds (1 hour)

    # logging
    log_level: str = "INFO"
    app_name: str = "ai-consumer"
    log_folder: str = "/var/log"


settings = Settings()
