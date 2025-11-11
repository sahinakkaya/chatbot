import logging
from typing import List

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class RAGHelper:
    """Helper class for Retrieval-Augmented Generation using OpenAI embeddings"""

    def __init__(
        self,
        openai_client: OpenAI,
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize RAG helper with embedding model and chunking parameters

        Args:
            openai_client: OpenAI client instance for making API calls
            embedding_model: Name of the OpenAI embedding model
            chunk_size: Number of characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        logger.info(f"Using OpenAI embedding model: {embedding_model}")
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[str] = []
        self.embeddings: np.ndarray = np.array([])

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: The text to chunk

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # Try to break at sentence boundaries
            if end < text_length:
                # Look for sentence endings near the chunk boundary
                chunk_end = text[start:end].rfind(". ")
                if chunk_end != -1 and chunk_end > self.chunk_size * 0.5:
                    end = start + chunk_end + 1
                else:
                    # Try newline as fallback
                    chunk_end = text[start:end].rfind("\n")
                    if chunk_end != -1 and chunk_end > self.chunk_size * 0.5:
                        end = start + chunk_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks

    def initialize_from_file(self, file_path: str):
        """
        Load context from file, chunk it, and create embeddings

        Args:
            file_path: Path to the context file
        """
        logger.info(f"Loading context from: {file_path}")
        with open(file_path) as f:
            text = f.read()

        self.initialize_from_text(text)

    def initialize_from_text(self, text: str):
        """
        Chunk text and create embeddings

        Args:
            text: The context text to process
        """
        # Chunk the text
        self.chunks = self.chunk_text(text)

        # Create embeddings for all chunks using OpenAI
        logger.info(f"Creating embeddings for {len(self.chunks)} chunks")
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=self.chunks
        )

        # Extract embeddings from response and convert to numpy array
        self.embeddings = np.array([item.embedding for item in response.data])

        logger.info(
            f"RAG initialized with {len(self.chunks)} chunks, embedding dimension: {self.embeddings.shape[1]}"
        )

    def retrieve_relevant_chunks(
        self, query: str, top_k: int = 3, min_similarity: float = 0.0
    ) -> List[str]:
        """
        Retrieve the most relevant chunks for a query using cosine similarity

        Args:
            query: The user's question
            top_k: Number of top chunks to retrieve
            min_similarity: Minimum similarity score (-1 to 1) to include a chunk

        Returns:
            List of relevant text chunks
        """
        if len(self.chunks) == 0:
            logger.warning("No chunks available for retrieval")
            return []

        # Get query embedding from OpenAI
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        query_embedding = np.array(response.data[0].embedding)

        # Normalize embeddings for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)

        # Calculate cosine similarity using dot product of normalized vectors
        similarities = np.dot(embeddings_norm, query_norm)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Filter by minimum similarity and retrieve chunks
        relevant_chunks = []
        for idx in top_indices:
            similarity = similarities[idx]
            if similarity >= min_similarity:
                relevant_chunks.append(self.chunks[idx])
                logger.debug(
                    f"Retrieved chunk {idx} with similarity {similarity:.3f}: {self.chunks[idx][:100]}..."
                )

        logger.info(
            f"Retrieved {len(relevant_chunks)} relevant chunks for query: '{query[:50]}...'"
        )
        return relevant_chunks
