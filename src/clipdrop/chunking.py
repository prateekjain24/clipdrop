"""Utilities for preparing chunked summarization requests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional
from uuid import uuid4

DEFAULT_MAX_CHUNK_CHARS = 12_000


@dataclass(slots=True)
class SummaryChunk:
    """Represents a chunk of text with derived metadata."""

    id: str
    index: int
    text: str
    char_length: int
    token_estimate: int
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_text(
        cls,
        index: int,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "SummaryChunk":
        stripped = text.strip()
        char_length = len(stripped)
        token_estimate = max(1, char_length // 4)  # Rough heuristic
        return cls(
            id=str(uuid4()),
            index=index,
            text=stripped,
            char_length=char_length,
            token_estimate=token_estimate,
            metadata=metadata,
        )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "index": self.index,
            "text": self.text,
            "char_length": self.char_length,
            "token_estimate": self.token_estimate,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(slots=True)
class ChunkingStrategy:
    """Configuration for the chunked summarization helper."""

    type: str = "hierarchical"
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS
    target_summary_sentences: int = 4
    language: str = "en-US"
    retry_attempt: int = 0

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "type": self.type,
            "max_chunk_chars": self.max_chunk_chars,
            "target_summary_sentences": self.target_summary_sentences,
            "language": self.language,
        }
        if self.retry_attempt:
            payload["retry_attempt"] = self.retry_attempt
        return payload


@dataclass(slots=True)
class ChunkedSummarizationRequest:
    """Container for the chunked summarization protocol payload."""

    content_format: str
    origin: str
    chunks: List[SummaryChunk]
    strategy: ChunkingStrategy
    instructions: Optional[str] = None
    version: str = "1.0"
    mode: str = "chunked"

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "mode": self.mode,
            "content_format": self.content_format,
            "origin": self.origin,
            "chunks": [chunk.to_payload() for chunk in self.chunks],
            "strategy": self.strategy.to_payload(),
        }
        if self.instructions:
            payload["instructions"] = self.instructions
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_payload())


def estimate_token_count(text: str) -> int:
    """Coarse token estimate sufficient for chunk sizing heuristics."""
    length = len(text.strip())
    if length == 0:
        return 0
    return max(1, length // 4)


def _split_into_paragraphs(content: str) -> list[str]:
    cleaned = content.strip()
    if not cleaned:
        return []
    # Keep paragraph boundaries while collapsing excessive blank lines
    paragraphs = [para.strip() for para in re.split(r"\n{2,}", cleaned) if para.strip()]
    return paragraphs or [cleaned]


def create_semantic_chunks(
    content: str,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    metadata: Optional[dict[str, Any]] = None,
) -> list[SummaryChunk]:
    """Split content into chunks beneath the helper's character limit."""

    if max_chunk_chars <= 0:
        raise ValueError("max_chunk_chars must be positive")

    paragraphs = _split_into_paragraphs(content)
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        delimiter = "\n\n" if current else ""
        projected_length = current_len + (len(delimiter) + paragraph_length)

        if projected_length <= max_chunk_chars:
            current.append(paragraph)
            current_len = projected_length
            continue

        if current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

        if paragraph_length <= max_chunk_chars:
            current = [paragraph]
            current_len = paragraph_length
            continue

        # Fallback: hard split oversized paragraph into equal slices
        for start in range(0, paragraph_length, max_chunk_chars):
            slice_text = paragraph[start:start + max_chunk_chars]
            chunks.append(slice_text)
        current = []
        current_len = 0

    if current:
        chunks.append("\n\n".join(current))

    # Merge trailing short chunk with previous when appropriate
    if len(chunks) >= 2 and len(chunks[-1]) < max_chunk_chars // 3:
        penultimate = chunks[-2]
        chunks[-2] = f"{penultimate}\n\n{chunks[-1]}".strip()
        chunks.pop()

    result: list[SummaryChunk] = []
    for index, chunk_text in enumerate(chunks):
        chunk_meta = metadata.copy() if metadata else None
        result.append(
            SummaryChunk(
                id=str(uuid4()),
                index=index,
                text=chunk_text,
                char_length=len(chunk_text),
                token_estimate=estimate_token_count(chunk_text),
                metadata=chunk_meta,
            )
        )
    return result


def build_chunked_request(
    content: str,
    content_format: str = "plaintext",
    origin: str = "clipdrop-cli",
    language: str = "en-US",
    instructions: Optional[str] = None,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    retry_attempt: int = 0,
    metadata: Optional[dict[str, Any]] = None,
) -> ChunkedSummarizationRequest:
    """Create a protocol-compliant request object for chunked summarization."""

    chunks = create_semantic_chunks(
        content,
        max_chunk_chars=max_chunk_chars,
        metadata=metadata,
    )

    strategy = ChunkingStrategy(
        max_chunk_chars=max_chunk_chars,
        language=language,
        retry_attempt=retry_attempt,
    )

    return ChunkedSummarizationRequest(
        content_format=content_format,
        origin=origin,
        instructions=instructions,
        chunks=chunks,
        strategy=strategy,
    )
