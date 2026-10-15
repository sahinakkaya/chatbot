from typing import Sequence

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    allow_origins: Sequence[str] = ["*"]
    allow_credentials: bool = False
    allow_methods: Sequence[str] = ["*"]
    allow_headers: Sequence[str] = ["*"]

    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    redis_host: str = "localhost"
    redis_port: int = 6379

    token_ttl: int = 3600
    user_rate_limit_max_requests: int = 10
    user_rate_limit_window_seconds: int = 60

    chat_history_max_messages: int = 20
    chat_history_ttl: int = 3600
    keep_history: bool = True

    context_file_path: str = "./data/resume-data.txt"
    rag_embedding_model: str = "text-embedding-3-large"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 3
    rag_min_similarity: float = 0.0

    system_prompt: str = """You are \"Şahin Akkaya\", a fullstack developer who sees the world as lines of code in the Matrix. When I ask questions, you will respond with answers that merge programming wisdom and Matrix references — as if you're explaining code from inside the simulation. Your tone should feel like Neo or Morpheus teaching coding through digital enlightenment."""

    turnstile_secret_key: str = ""

    log_level: str = "INFO"
    app_name: str = "chatbot"
    log_folder: str = "/var/log"


settings = Settings()
