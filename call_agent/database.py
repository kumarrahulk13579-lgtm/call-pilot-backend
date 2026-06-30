"""SQLAlchemy engine and session for the app (reads DATABASE_URL)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. See .env.example.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
