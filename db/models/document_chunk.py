from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func

from .base import Base

EMBED_DIM = 1536  # must match the Azure embeddings model (text-embedding-3-small)


class DocumentChunk(Base):
    """A chunk of a document plus its embedding, for retrieval at call time."""

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBED_DIM), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
