from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func

from .base import Base


class Agent(Base):
    """A user-created call agent: a persona + voice the caller talks to."""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False, server_default="custom", index=True)
    name = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    greeting = Column(Text, nullable=True)
    voice = Column(String, nullable=False, server_default="alloy")
    instructions = Column(Text, nullable=True)  # tone / accent steering for TTS
    config = Column(JSON, nullable=True)  # per-type feature config (questions, slots, ...)
    created_at = Column(DateTime, server_default=func.now())
