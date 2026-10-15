import logging
from typing import List

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class RAGHelper:
    def __init__(
        self,
        openai_client: OpenAI,
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[str] = []
        self.embeddings: np.ndarray = np.array([])

    def chunk_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end < len(text):
                chunk_end = text[start:end].rfind(". ")
                if chunk_end == -1 or chunk_end <= self.chunk_size * 0.5:
                    chunk_end = text[start:end].rfind("\n")
                if chunk_end > self.chunk_size * 0.5:
                    end = start + chunk_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks

    def initialize_from_file(self, file_path: str):
        logger.info(f"Loading context from: {file_path}")
        with open(file_path) as context_file:
            self.initialize_from_text(context_file.read())

    def initialize_from_text(self, text: str):
        self.chunks = self.chunk_text(text)
        logger.info(f"Creating embeddings for {len(self.chunks)} chunks")
        response = self.openai_client.embeddings.create(
            model=self.embedding_model, input=self.chunks
        )
        self.embeddings = np.array([item.embedding for item in response.data])

    def retrieve_relevant_chunks(
        self, query: str, top_k: int = 3, min_similarity: float = 0.0
    ) -> List[str]:
        if not self.chunks:
            return []

        response = self.openai_client.embeddings.create(
            model=self.embedding_model, input=query
        )
        query_embedding = np.array(response.data[0].embedding)
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = self.embeddings / np.linalg.norm(
            self.embeddings, axis=1, keepdims=True
        )
        similarities = np.dot(embeddings_norm, query_norm)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [
            self.chunks[index]
            for index in top_indices
            if similarities[index] >= min_similarity
        ]
