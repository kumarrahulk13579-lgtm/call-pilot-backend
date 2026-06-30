"""Knowledge-base document management for customer-care agents (auth + ownership)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from call_agent import rag
from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig
from call_agent.database import get_db
from call_agent.security import get_current_user
from db.models import Agent, Document, DocumentChunk, User

router = APIRouter(tags=["documents"])

_client = AzureOpenAIClient(AzureOpenAIConfig.from_env())


class AddDocumentRequest(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class AddDocumentResponse(BaseModel):
    document_id: int
    title: str
    chunks: int


class DocumentResponse(BaseModel):
    id: int
    title: str
    created_at: datetime | None = None


def _owned_agent(agent_id: int, db: Session, user: User) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("/agents/{agent_id}/documents", response_model=AddDocumentResponse)
def add_document(
    agent_id: int,
    body: AddDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AddDocumentResponse:
    _owned_agent(agent_id, db, current_user)
    document, chunk_count = rag.ingest_document(
        db, _client, agent_id, body.title, body.text
    )
    return AddDocumentResponse(
        document_id=document.id, title=document.title, chunks=chunk_count
    )


@router.get("/agents/{agent_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    _owned_agent(agent_id, db, current_user)
    docs = db.query(Document).filter(Document.agent_id == agent_id).all()
    return [DocumentResponse(id=d.id, title=d.title, created_at=d.created_at) for d in docs]


@router.delete("/agents/{agent_id}/documents/{doc_id}")
def delete_document(
    agent_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _owned_agent(agent_id, db, current_user)
    document = db.get(Document, doc_id)
    if document is None or document.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    db.delete(document)
    db.commit()
    return {"deleted": doc_id}
