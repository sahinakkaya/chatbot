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

    # RAG (Retrieval-Augmented Generation)
    context_file_path: str = "./resume-data.txt"
    rag_embedding_model: str = "text-embedding-3-large"  # OpenAI embedding model
    rag_chunk_size: int = 500  # Number of characters per chunk
    rag_chunk_overlap: int = 50  # Overlapping characters between chunks
    rag_top_k: int = 3  # Number of relevant chunks to retrieve per query
    rag_min_similarity: float = 0.0  # Minimum similarity score to include a chunk (-1 to 1)

    # AI System Prompt
    system_prompt: str = """You are "Şahin Akkaya", a fullstack developer who sees the world as lines of code in the Matrix. When I ask questions, you will respond with answers that merge programming wisdom and Matrix references — as if you're explaining code from inside the simulation. Your tone should feel like Neo or Morpheus teaching coding through digital enlightenment."""

    # logging
    log_level: str = "INFO"
    app_name: str = "ai-consumer"
    log_folder: str = "/var/log"


settings = Settings()
