"""FastAPI server exposing Twilio voice webhooks for the call agents.

Two ways in:
  - Default agent:  POST /voice            + /respond
  - User agents:    POST /a/{slug}/voice   + /a/{slug}/respond

Flow (turn-based, inbound):
  Twilio  -> POST .../voice    : call begins; we greet and start listening.
  Twilio  -> POST .../respond  : caller's speech transcript arrives; we reply and listen.

Twilio handles speech-to-text (<Gather input="speech">). Azure OpenAI generates the
reply text and the spoken voice (gpt-4o-mini-tts, served as MP3 via <Play>).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Depends, FastAPI, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import Gather, VoiceResponse

from call_agent import rag
from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig
from call_agent.conversation import SYSTEM_PROMPT, ConversationStore
from call_agent.database import get_db
from call_agent.web.agent_routes import router as agent_router
from call_agent.web.auth_routes import router as auth_router
from call_agent.web.document_routes import router as document_router
from call_agent.web.voice_test_routes import router as voice_test_router
from db.models import Agent

GREETING = "Hi! You're speaking with the AI call agent. How can I help you today?"
NO_SPEECH_REPROMPT = "Sorry, I didn't catch that. Could you say it again?"
GOODBYE_WORDS = ("bye", "goodbye", "hang up", "that's all", "thank you, bye")

# Default Azure TTS voice (gpt-4o-mini-tts). Options: alloy, echo, fable, onyx, nova, shimmer.
TTS_VOICE = "alloy"

app = FastAPI(title="CallPilot Call Agent")
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(document_router)
app.include_router(voice_test_router)
client = AzureOpenAIClient(AzureOpenAIConfig.from_env())
conversations = ConversationStore(client)

# Generated speech clips, keyed by id, that Twilio fetches via <Play>.
_audio_clips: dict[str, bytes] = {}


@dataclass
class AgentSpec:
    """The bits of an agent needed to run one turn of a call."""

    system_prompt: str
    greeting: str
    voice: str
    instructions: str | None
    base_path: str = ""  # "" -> /voice,/respond ; "/a/<slug>" -> dynamic routes
    agent_id: int | None = None
    agent_type: str = ""

    @property
    def respond_url(self) -> str:
        return f"{self.base_path}/respond"

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentSpec":
        return cls(
            system_prompt=agent.system_prompt,
            greeting=agent.greeting or GREETING,
            voice=agent.voice,
            instructions=agent.instructions,
            base_path=f"/a/{agent.slug}",
            agent_id=agent.id,
            agent_type=agent.type,
        )


DEFAULT_SPEC = AgentSpec(
    system_prompt=SYSTEM_PROMPT,
    greeting=GREETING,
    voice=TTS_VOICE,
    instructions=None,
)


def _voice_clip(text: str, voice: str = TTS_VOICE, instructions: str | None = None) -> str:
    """Synthesize `text` with Azure TTS, cache it, return its relative <Play> URL."""
    clip_id = uuid4().hex
    _audio_clips[clip_id] = client.text_to_speech(text, voice=voice, instructions=instructions)
    return f"/audio/{clip_id}.mp3"


def _listen(response: VoiceResponse, spec: AgentSpec, prompt: str | None = None) -> None:
    """Speak an optional prompt, then gather the caller's next spoken turn."""
    gather = Gather(
        input="speech",
        speech_timeout="auto",
        action=spec.respond_url,
        method="POST",
    )
    if prompt:
        gather.play(_voice_clip(prompt, spec.voice, spec.instructions))
    response.append(gather)
    # If the caller says nothing, Gather falls through to here.
    response.redirect(spec.respond_url, method="POST")


def _twiml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type="application/xml")


def _handle_voice(spec: AgentSpec) -> Response:
    response = VoiceResponse()
    _listen(response, spec, spec.greeting)
    return _twiml(response)


def _handle_respond(
    spec: AgentSpec, call_sid: str, speech: str, db: Session | None = None
) -> Response:
    response = VoiceResponse()
    user_text = speech.strip()

    if not user_text:
        _listen(response, spec, NO_SPEECH_REPROMPT)
        return _twiml(response)

    context = None
    if spec.agent_type == "customer_care" and spec.agent_id and db is not None:
        chunks = rag.retrieve(db, client, spec.agent_id, user_text)
        if chunks:
            context = "\n\n".join(chunks)

    reply = conversations.generate_reply(call_sid, user_text, spec.system_prompt, context)
    response.play(_voice_clip(reply, spec.voice, spec.instructions))

    if any(word in user_text.lower() for word in GOODBYE_WORDS):
        response.play(_voice_clip("Goodbye!", spec.voice, spec.instructions))
        response.hangup()
        conversations.end(call_sid)
        return _twiml(response)

    _listen(response, spec)
    return _twiml(response)


def _spec_for_slug(slug: str, db: Session) -> AgentSpec | None:
    agent = db.query(Agent).filter(Agent.slug == slug).first()
    return AgentSpec.from_agent(agent) if agent is not None else None


def _agent_not_found() -> Response:
    response = VoiceResponse()
    response.say("Sorry, this agent is not available.")
    response.hangup()
    return _twiml(response)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/audio/{clip_id}.mp3")
def audio(clip_id: str) -> Response:
    data = _audio_clips.pop(clip_id, None)
    if data is None:
        return Response(status_code=404)
    return Response(content=data, media_type="audio/mpeg")


# --- Default agent --------------------------------------------------------------


@app.post("/voice")
def voice() -> Response:
    return _handle_voice(DEFAULT_SPEC)


@app.post("/respond")
def respond(CallSid: str = Form(default=""), SpeechResult: str = Form(default="")) -> Response:
    return _handle_respond(DEFAULT_SPEC, CallSid, SpeechResult)


# --- User-created agents --------------------------------------------------------


@app.post("/a/{slug}/voice")
def agent_voice(slug: str, db: Session = Depends(get_db)) -> Response:
    spec = _spec_for_slug(slug, db)
    return _handle_voice(spec) if spec else _agent_not_found()


@app.post("/a/{slug}/respond")
def agent_respond(
    slug: str,
    CallSid: str = Form(default=""),
    SpeechResult: str = Form(default=""),
    db: Session = Depends(get_db),
) -> Response:
    spec = _spec_for_slug(slug, db)
    return _handle_respond(spec, CallSid, SpeechResult, db) if spec else _agent_not_found()


def run() -> None:
    """Entry point for the `call-pilot-serve` script."""
    import uvicorn

    uvicorn.run("call_agent.web.app:app", host="0.0.0.0", port=8000, reload=True)
