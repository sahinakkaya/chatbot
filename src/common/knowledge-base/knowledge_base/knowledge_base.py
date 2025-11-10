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
            data_path: Path to resume data file (.txt, .md, or .json)
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
        Load resume data from file and create embeddings.

        Supports TXT, Markdown, and JSON files. TXT is recommended for simplicity.
        """
        path = Path(data_path)

        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        logger.info(f"Loading knowledge base from: {data_path}")

        if path.suffix in [".txt", ".md"]:
            self._load_text(data_path)
        elif path.suffix == ".json":
            self._load_json(data_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}. Use .txt, .md, or .json")

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

    def _load_text(self, file_path: str) -> None:
        """
        Load text file and split into semantic chunks.

        Chunks are created by:
        1. Splitting by markdown headers (# SECTION)
        2. Splitting by double newlines (paragraphs)
        3. Filtering out very short chunks
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = []
        current_section = ""
        current_chunk = []

        lines = content.split('\n')

        for line in lines:
            # Check if it's a markdown header
            if line.startswith('#'):
                # Save previous chunk if it exists
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if len(chunk_text) > 20:  # Minimum chunk length
                        chunks.append({
                            "content": chunk_text,
                            "metadata": {"section": current_section, "source": "text"}
                        })
                    current_chunk = []

                # Update current section
                current_section = line.lstrip('#').strip()
                current_chunk.append(line)

            elif line.strip() == '':
                # Empty line - potential paragraph boundary
                if current_chunk:
                    # Check if we have enough content for a chunk
                    chunk_text = '\n'.join(current_chunk).strip()
                    if len(chunk_text) > 30:  # Minimum paragraph length
                        chunks.append({
                            "content": chunk_text,
                            "metadata": {"section": current_section, "source": "text"}
                        })
                        current_chunk = []
                    else:
                        # Keep accumulating if chunk is too small
                        current_chunk.append(line)
            else:
                current_chunk.append(line)

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if len(chunk_text) > 20:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {"section": current_section, "source": "text"}
                })

        self.chunks = chunks
        logger.info(f"Created {len(chunks)} chunks from text file")

    def _structure_to_chunks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert structured resume JSON into searchable text chunks.

        Creates natural language chunks that match well with questions.
        """
        chunks = []

        # Process each section of the resume
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested structure (e.g., personal info, contact, skills)
                # Create natural language chunks for better semantic matching
                if key == "personal":
                    for k, v in value.items():
                        if k == "name":
                            chunks.append({
                                "content": f"The person's name is {v}. His name is {v}.",
                                "metadata": {"section": key, "field": k, "type": "info"}
                            })
                        elif k == "location":
                            chunks.append({
                                "content": f"He is located in {v}. He lives in {v}. His location is {v}.",
                                "metadata": {"section": key, "field": k, "type": "info"}
                            })
                        elif k == "title":
                            chunks.append({
                                "content": f"He is a {v}. His job title is {v}. He works as a {v}.",
                                "metadata": {"section": key, "field": k, "type": "info"}
                            })
                        elif k in ["email", "website", "github", "linkedin", "stackoverflow"]:
                            chunks.append({
                                "content": f"His {k} is {v}. You can find him at {v}.",
                                "metadata": {"section": key, "field": k, "type": "info"}
                            })
                elif key == "skills":
                    # Special handling for skills - create natural language chunks
                    all_skills = []
                    for category, skill_list in value.items():
                        if isinstance(skill_list, list):
                            skills_str = ", ".join(skill_list)
                            chunks.append({
                                "content": f"His {category} include: {skills_str}. He has experience with {skills_str}.",
                                "metadata": {"section": key, "category": category, "type": "info"}
                            })
                            all_skills.extend(skill_list)

                    # Also create a general skills chunk
                    if all_skills:
                        chunks.append({
                            "content": f"His technical skills include: {', '.join(all_skills)}. He is proficient in {', '.join(all_skills[:5])}.",
                            "metadata": {"section": key, "type": "info"}
                        })
                else:
                    # Generic dict handling
                    chunk_content = f"{key}: " + ", ".join(
                        f"{k}: {v}" for k, v in value.items() if v
                    )
                    chunks.append({
                        "content": chunk_content,
                        "metadata": {"section": key, "type": "info"},
                    })

            elif isinstance(value, list):
                # List items (e.g., experience, education, skills)
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        # Special handling for education
                        if key == "education":
                            school = item.get("school", "")
                            degree = item.get("degree", "")
                            duration = item.get("duration", "")
                            location = item.get("location", "")
                            gpa = item.get("gpa", "")
                            courses = item.get("courses", "")

                            # Create natural language chunk
                            parts = []
                            if school and degree:
                                parts.append(f"He graduated from {school} with a {degree}")
                            elif school:
                                parts.append(f"He studied at {school}")

                            if duration:
                                parts.append(f"from {duration}")

                            if location:
                                parts.append(f"in {location}")

                            if gpa:
                                parts.append(f"with a GPA of {gpa}")

                            if courses:
                                parts.append(f"His relevant courses included {courses}")

                            chunk_content = ". ".join(parts) + "."

                        # Special handling for experience
                        elif key == "experience":
                            title = item.get("title", "")
                            company = item.get("company", "")
                            duration = item.get("duration", "")
                            location = item.get("location", "")
                            work_type = item.get("type", "")
                            technologies = item.get("technologies", "")
                            description = item.get("description", "")

                            parts = []
                            if title and company:
                                parts.append(f"He worked as a {title} at {company}")

                            if duration:
                                parts.append(f"from {duration}")

                            if location:
                                parts.append(f"({location})")

                            if work_type:
                                parts.append(f"This was a {work_type} position")

                            if technologies:
                                parts.append(f"Technologies used: {technologies}")

                            if description:
                                parts.append(f"{description}")

                            chunk_content = ". ".join(parts) + "."

                        # Special handling for projects
                        elif key == "projects":
                            name = item.get("name", "")
                            description = item.get("description", "")
                            technologies = item.get("technologies", "")
                            project_type = item.get("type", "")
                            link = item.get("link", "")

                            parts = []
                            if name:
                                parts.append(f"Project: {name}")

                            if project_type:
                                parts.append(f"({project_type})")

                            if description:
                                parts.append(description)

                            if technologies:
                                parts.append(f"Built with: {technologies}")

                            if link:
                                parts.append(f"Link: {link}")

                            chunk_content = ". ".join(parts) + "."

                        else:
                            # Generic dict handling
                            chunk_content = f"{key}: " + ". ".join(
                                f"{k}: {v}" for k, v in item.items() if v
                            )
                    else:
                        chunk_content = f"{key}: {item}"

                    chunks.append({
                        "content": chunk_content,
                        "metadata": {"section": key, "index": idx, "type": "list"},
                    })

            elif isinstance(value, str):
                # Simple string values with natural language
                if key == "about":
                    chunks.append({
                        "content": f"About him: {value}. He is {value}.",
                        "metadata": {"section": key, "type": "text"},
                    })
                elif key == "summary":
                    chunks.append({
                        "content": f"Summary: {value}",
                        "metadata": {"section": key, "type": "text"},
                    })
                else:
                    chunks.append({
                        "content": f"{key}: {value}",
                        "metadata": {"section": key, "type": "text"},
                    })

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

    def search(self, query: str, top_k: int = 3, threshold: float = 0.25) -> List[RetrievalResult]:
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
        top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Get more candidates
        results = []

        # Log top scores for debugging
        logger.debug(f"Query: '{query}'")
        logger.debug(f"Top 5 similarity scores: {[float(similarities[i]) for i in top_indices[:5]]}")

        for idx in top_indices[:top_k]:
            score = float(similarities[idx])
            logger.debug(f"Candidate chunk (score={score:.3f}): {self.chunks[idx]['content'][:100]}...")

            if score >= threshold:
                results.append(
                    RetrievalResult(
                        content=self.chunks[idx]["content"],
                        score=score,
                        metadata=self.chunks[idx].get("metadata", {}),
                    )
                )

        if results:
            logger.info(
                f"Search for '{query}' returned {len(results)} results with scores: {[f'{r.score:.3f}' for r in results]}"
            )
        else:
            logger.warning(
                f"Search for '{query}' returned 0 results. Top score was {float(similarities[top_indices[0]]):.3f}, threshold is {threshold}"
            )

        return results

    def get_context_for_query(
        self, query: str, max_chunks: int = 3, threshold: float = 0.25
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
