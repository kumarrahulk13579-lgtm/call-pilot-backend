"""Retrieval-augmented generation for customer-care agents.

Ingest pasted text -> chunk -> embed (Azure) -> store in pgvector. At call time,
embed the caller's question and retrieve the most similar chunks for that agent.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from call_agent.azure_openai import AzureOpenAIClient
from db.models import Document, DocumentChunk

CHUNK_WORDS = 200       # ~chunk size in words
CHUNK_OVERLAP = 40      # words shared between consecutive chunks
DEFAULT_TOP_K = 4


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping word-windows."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(CHUNK_WORDS - CHUNK_OVERLAP, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + CHUNK_WORDS])
        if chunk:
            chunks.append(chunk)
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def ingest_document(
    db: Session, client: AzureOpenAIClient, agent_id: int, title: str, text: str
) -> tuple[Document, int]:
    """Store a document and its embedded chunks. Returns (document, chunk_count)."""
    document = Document(agent_id=agent_id, title=title)
    db.add(document)
    db.flush()  # assign document.id

    chunks = chunk_text(text)
    if chunks:
        embeddings = client.embed(chunks)
        for content, embedding in zip(chunks, embeddings):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    agent_id=agent_id,
                    content=content,
                    embedding=embedding,
                )
            )
    db.commit()
    db.refresh(document)
    return document, len(chunks)


def retrieve(
    db: Session, client: AzureOpenAIClient, agent_id: int, query: str, k: int = DEFAULT_TOP_K
) -> list[str]:
    """Return the top-k chunk texts most relevant to `query` for this agent."""
    query_embedding = client.embed([query])[0]
    rows = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.agent_id == agent_id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(k)
        .all()
    )
    return [row.content for row in rows]
