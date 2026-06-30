"""Authenticated endpoints to create and list a user's call agents.

Creating an agent returns the webhook URL the user pastes into their Twilio number.
An agent has a `type` (customer_care, call_screener, ...) whose template prefills the
persona/voice; the user can override any field.
"""

from __future__ import annotations

import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from call_agent.agent_templates import TEMPLATES, VALID_TYPES, get_template
from call_agent.database import get_db
from call_agent.security import get_current_user
from db.models import Agent, User

router = APIRouter(tags=["agents"])


class CreateAgentRequest(BaseModel):
    type: str = Field(description=f"One of: {', '.join(VALID_TYPES)}")
    name: str | None = None
    system_prompt: str | None = None
    greeting: str | None = None
    voice: str | None = None
    instructions: str | None = None  # tone / accent steering for the voice
    config: dict | None = None  # per-type feature config (questions, slots, ...)


class AgentResponse(BaseModel):
    id: int
    slug: str
    type: str
    name: str
    system_prompt: str
    greeting: str | None = None
    voice: str
    instructions: str | None = None
    config: dict
    webhook_url: str


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    greeting: str | None = None
    voice: str | None = None
    instructions: str | None = None
    config: dict | None = None


class TemplateResponse(BaseModel):
    type: str
    label: str
    description: str
    system_prompt: str
    greeting: str | None = None
    voice: str
    instructions: str | None = None
    config: dict


def _webhook_url(slug: str) -> str:
    """The /voice URL to paste into Twilio. Uses PUBLIC_BASE_URL if set."""
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/a/{slug}/voice" if base else f"/a/{slug}/voice"


def _to_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        slug=agent.slug,
        type=agent.type,
        name=agent.name,
        system_prompt=agent.system_prompt,
        greeting=agent.greeting,
        voice=agent.voice,
        instructions=agent.instructions,
        config=agent.config or {},
        webhook_url=_webhook_url(agent.slug),
    )


@router.get("/agent-templates", response_model=list[TemplateResponse])
def list_templates() -> list[TemplateResponse]:
    return [TemplateResponse(**t) for t in TEMPLATES]


@router.post("/agents", response_model=AgentResponse)
def create_agent(
    body: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    if body.type not in VALID_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown type '{body.type}'. Valid: {', '.join(VALID_TYPES)}",
        )

    template = get_template(body.type)

    # Start from template defaults, override with any explicitly-provided fields.
    system_prompt = body.system_prompt or template["system_prompt"]
    if not system_prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="system_prompt is required for a custom agent",
        )

    agent = Agent(
        slug=f"ag_{uuid4().hex[:10]}",
        user_id=current_user.id,
        type=body.type,
        name=body.name or template["label"],
        system_prompt=system_prompt,
        greeting=body.greeting if body.greeting is not None else template["greeting"],
        voice=body.voice or template["voice"],
        instructions=(
            body.instructions if body.instructions is not None else template["instructions"]
        ),
        config=body.config if body.config is not None else template["config"],
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _to_response(agent)


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentResponse]:
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).all()
    return [_to_response(a) for a in agents]


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _to_response(agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: int,
    body: UpdateAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return _to_response(agent)
