import asyncio
import json
import logging
import time
from datetime import UTC, datetime

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from chatbot.config import settings
from chatbot.rag_helper import RAGHelper
from chatbot.util import redis_helper

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.openai_client: OpenAI | None = None
        self.rag_helper: RAGHelper | None = None

    def initialize(self):
        self.openai_client = OpenAI(api_key=settings.openai_api_key, max_retries=0)
        self.rag_helper = RAGHelper(
            openai_client=self.openai_client,
            embedding_model=settings.rag_embedding_model,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        self.rag_helper.initialize_from_file(settings.context_file_path)
        logger.info("AI service initialized with retrieval-augmented generation")

    async def get_conversation_history(self, userid: str) -> list[dict]:
        if not settings.keep_history:
            return []
        try:
            history_json = await redis_helper.get(f"chat_history:{userid}")
            return json.loads(history_json) if history_json else []
        except Exception as error:
            logger.error(
                f"Failed to retrieve conversation history for user {userid}: {error}"
            )
            return []

    async def update_conversation_history(
        self, userid: str, user_message: str, ai_response: str
    ):
        if not settings.keep_history:
            return
        try:
            history = await self.get_conversation_history(userid)
            history.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": ai_response},
                ]
            )
            history = history[-settings.chat_history_max_messages :]
            await redis_helper.set(
                f"chat_history:{userid}",
                json.dumps(history),
                ex=settings.chat_history_ttl,
            )
        except Exception as error:
            logger.error(
                f"Failed to update conversation history for user {userid}: {error}"
            )

    async def create_response(
        self, userid: str, content: str, correlation_id: str
    ) -> dict:
        start_time = time.time()
        ai_response = await self.process_with_openai(userid, content)
        await self.update_conversation_history(userid, content, ai_response)
        return {
            "type": "response",
            "content": ai_response,
            "userid": userid,
            "timestamp": datetime.now(UTC).isoformat(),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "correlation_id": correlation_id,
        }

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(7),
        wait=wait_exponential(),
        reraise=True,
    )
    async def process_with_openai(self, userid: str, content: str) -> str:
        if self.openai_client is None or self.rag_helper is None:
            raise RuntimeError("AI service is not initialized")

        history = await self.get_conversation_history(userid)
        relevant_chunks = await asyncio.to_thread(
            self.rag_helper.retrieve_relevant_chunks,
            content,
            settings.rag_top_k,
            settings.rag_min_similarity,
        )

        system_content = settings.system_prompt
        if relevant_chunks:
            system_content = f"""{settings.system_prompt}

Use the following information to answer questions if you need. It is written by Şahin Akkaya himself.

Context:
{"\n\n".join(relevant_chunks)}
"""

        messages = [{"role": "system", "content": system_content}, *history]
        messages.append({"role": "user", "content": content})
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model=settings.openai_model,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
            timeout=2.0,
        )
        return response.choices[0].message.content
