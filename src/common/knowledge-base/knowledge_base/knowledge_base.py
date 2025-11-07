"""
Knowledge Base service for RAG (Retrieval-Augmented Generation).

Uses sentence-transformers for local, free embeddings.
Implements semantic search over resume data.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Result from knowledge base retrieval"""

    content: str
    score: float
    metadata: Dict[str, Any] = {}


class KnowledgeBase:
    """
    Knowledge base for semantic search over structured data.

    Uses sentence-transformers for embeddings (free, local, no API calls).
    """

    def __init__(
        self,
        data_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize knowledge base.

        Args:
            data_path: Path to resume-data.json
            model_name: Sentence-transformers model name (default: all-MiniLM-L6-v2)
                        This is a small, fast, high-quality model (~80MB)
        """
        self.data_path = data_path
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None

        # Load sentence-transformers model (local, no API calls)
        logger.info(f"Loading sentence-transformers model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info("Model loaded successfully")

        # Load and process data if path provided
        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str) -> None:
        """
        Load resume data from JSON file and create embeddings.

        Supports both structured JSON and markdown files.
        """
        path = Path(data_path)

        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        logger.info(f"Loading knowledge base from: {data_path}")

        if path.suffix == ".json":
            self._load_json(data_path)
        elif path.suffix == ".md":
            self._load_markdown(data_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        # Create embeddings for all chunks
        self._create_embeddings()

        logger.info(
            f"Knowledge base loaded: {len(self.chunks)} chunks, {self.embeddings.shape if self.embeddings is not None else 0} embeddings"
        )

    def _load_json(self, file_path: str) -> None:
        """Load structured JSON resume data"""
        with open(file_path, "r") as f:
            data = json.load(f)

        # Convert structured data into searchable chunks
        self.chunks = self._structure_to_chunks(data)

    def _load_markdown(self, file_path: str) -> None:
        """Load markdown file and split into chunks"""
        with open(file_path, "r") as f:
            content = f.read()

        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        self.chunks = [
            {"content": para, "metadata": {"source": "markdown"}}
            for para in paragraphs
        ]

    def _structure_to_chunks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert structured resume JSON into searchable text chunks.

        Creates semantic chunks that can answer specific questions.
        """
        chunks = []

        # Process each section of the resume
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested structure (e.g., personal info, contact)
                chunk_content = f"{key}: " + ", ".join(
                    f"{k}: {v}" for k, v in value.items() if v
                )
                chunks.append(
                    {
                        "content": chunk_content,
                        "metadata": {"section": key, "type": "info"},
                    }
                )

            elif isinstance(value, list):
                # List items (e.g., experience, education, skills)
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        # Convert dict to readable text
                        chunk_content = f"{key}: " + ". ".join(
                            f"{k}: {v}" for k, v in item.items() if v
                        )
                    else:
                        chunk_content = f"{key}: {item}"

                    chunks.append(
                        {
                            "content": chunk_content,
                            "metadata": {"section": key, "index": idx, "type": "list"},
                        }
                    )

            elif isinstance(value, str):
                # Simple string values
                chunks.append(
                    {
                        "content": f"{key}: {value}",
                        "metadata": {"section": key, "type": "text"},
                    }
                )

        return chunks

    def _create_embeddings(self) -> None:
        """Create embeddings for all chunks using sentence-transformers"""
        if not self.chunks:
            logger.warning("No chunks to embed")
            return

        # Extract text content from chunks
        texts = [chunk["content"] for chunk in self.chunks]

        # Create embeddings (local, no API calls)
        logger.info(f"Creating embeddings for {len(texts)} chunks...")
        self.embeddings = self.model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        logger.info("Embeddings created successfully")

    def search(self, query: str, top_k: int = 3, threshold: float = 0.3) -> List[RetrievalResult]:
        """
        Search knowledge base for relevant information.

        Args:
            query: User's question
            top_k: Number of top results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of RetrievalResult with relevant chunks
        """
        if not self.chunks or self.embeddings is None:
            logger.warning("Knowledge base is empty or not initialized")
            return []

        # Create embedding for query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

        # Calculate cosine similarity with all chunks
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k results above threshold
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []

        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append(
                    RetrievalResult(
                        content=self.chunks[idx]["content"],
                        score=score,
                        metadata=self.chunks[idx].get("metadata", {}),
                    )
                )

        logger.info(
            f"Search for '{query}' returned {len(results)} results (threshold: {threshold})"
        )

        return results

    def get_context_for_query(
        self, query: str, max_chunks: int = 3, threshold: float = 0.3
    ) -> tuple[str, float]:
        """
        Get formatted context string for AI prompt.

        Returns:
            Tuple of (context_string, max_confidence_score)
        """
        results = self.search(query, top_k=max_chunks, threshold=threshold)

        if not results:
            return "", 0.0

        # Format results into context string
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[{i}] {result.content}")

        context = "\n".join(context_parts)
        max_score = max(r.score for r in results)

        return context, max_score
