"""Voice-test endpoints: let users test an agent by speaking into their browser mic.

Flow:
  POST /agents/{id}/voice-test/start    → greeting MP3 + X-Session-Id header
  POST /agents/{id}/voice-test/respond  → send mic audio, get reply MP3 back
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from call_agent import rag
from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig
from call_agent.conversation import ConversationStore
from call_agent.database import get_db
from call_agent.security import get_current_user
from db.models import Agent, User

router = APIRouter(tags=["voice-test"])

_client = AzureOpenAIClient(AzureOpenAIConfig.from_env())
_conversations = ConversationStore(_client)

NO_SPEECH = "Sorry, I didn't catch that. Could you say it again?"


def _get_agent(agent_id: int, db: Session, current_user: User) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _tts(agent: Agent, text: str) -> bytes:
    return _client.text_to_speech(text, voice=agent.voice, instructions=agent.instructions)


@router.post("/agents/{agent_id}/voice-test/start")
def voice_test_start(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    agent = _get_agent(agent_id, db, current_user)
    session_id = f"vt_{uuid4().hex}"
    greeting = agent.greeting or "Hi! How can I help you today?"
    audio = _tts(agent, greeting)
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-Session-Id": session_id},
    )


@router.post("/agents/{agent_id}/voice-test/respond")
def voice_test_respond(
    agent_id: int,
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    agent = _get_agent(agent_id, db, current_user)

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio.file.read())
        tmp_path = tmp.name

    try:
        transcript = _client.transcribe(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not transcript.strip():
        return Response(
            content=_tts(agent, NO_SPEECH),
            media_type="audio/mpeg",
            headers={"X-Session-Id": session_id, "X-Transcript": ""},
        )

    context = None
    if agent.type == "customer_care":
        chunks = rag.retrieve(db, _client, agent.id, transcript)
        if chunks:
            context = "\n\n".join(chunks)

    reply = _conversations.generate_reply(session_id, transcript, agent.system_prompt, context)

    return Response(
        content=_tts(agent, reply),
        media_type="audio/mpeg",
        headers={
            "X-Session-Id": session_id,
            "X-Transcript": transcript,
            "X-Reply": reply,
        },
    )
