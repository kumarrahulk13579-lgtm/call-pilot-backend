from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from .base import Base


class Document(Base):
    """A knowledge-base document attached to a customer-care agent."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
