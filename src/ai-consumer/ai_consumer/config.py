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

    # Knowledge Base / RAG
    knowledge_base_path: str = "./resume-data.txt"
    rag_max_chunks: int = 3  # Number of context chunks to retrieve
    rag_confidence_threshold: float = 0.25  # Minimum similarity score (lower = more permissive)

    # Response Caching
    enable_caching: bool = True
    cache_ttl_seconds: int = 86400  # 24 hours

    # Cost Controls
    max_tokens_per_response: int = 300  # Lower than before (was 500) for cost savings

    # System Prompt
    system_prompt_template: str = """You are a helpful AI assistant answering questions about a person's professional background, skills, and experience.

Be concise, friendly, and professional. Keep responses under 3-4 sentences unless more detail is specifically requested."""

    # logging
    log_level: str = "INFO"
    app_name: str = "ai-consumer"
    log_folder: str = "/var/log"


settings = Settings()
