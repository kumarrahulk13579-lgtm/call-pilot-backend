"""FastAPI server exposing Twilio voice webhooks for the simple call agent.

Flow (turn-based, inbound):
  Twilio  -> POST /voice    : call begins; we greet and start listening.
  Twilio  -> POST /respond  : caller's speech transcript arrives; we reply and listen again.

Twilio handles speech-to-text (<Gather input="speech">) and text-to-speech (<Say>).
Azure OpenAI only generates the reply text.
"""

from __future__ import annotations

from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig
from call_agent.conversation import ConversationStore

GREETING = "Hi! You're speaking with the AI call agent. How can I help you today?"
NO_SPEECH_REPROMPT = "Sorry, I didn't catch that. Could you say it again?"
GOODBYE_WORDS = ("bye", "goodbye", "hang up", "that's all", "thank you, bye")

app = FastAPI(title="CallPilot Call Agent")
conversations = ConversationStore(AzureOpenAIClient(AzureOpenAIConfig.from_env()))


def _listen(response: VoiceResponse, prompt: str | None = None) -> None:
    """Speak an optional prompt, then gather the caller's next spoken turn."""
    gather = Gather(
        input="speech",
        speech_timeout="auto",
        action="/respond",
        method="POST",
    )
    if prompt:
        gather.say(prompt)
    response.append(gather)
    # If the caller says nothing, Gather falls through to here.
    response.redirect("/respond", method="POST")


def _twiml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type="application/xml")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/voice")
def voice() -> Response:
    response = VoiceResponse()
    _listen(response, GREETING)
    return _twiml(response)


@app.post("/respond")
def respond(
    CallSid: str = Form(default=""),
    SpeechResult: str = Form(default=""),
) -> Response:
    response = VoiceResponse()
    user_text = SpeechResult.strip()

    if not user_text:
        _listen(response, NO_SPEECH_REPROMPT)
        return _twiml(response)

    reply = conversations.generate_reply(CallSid, user_text)
    response.say(reply)

    if any(word in user_text.lower() for word in GOODBYE_WORDS):
        response.say("Goodbye!")
        response.hangup()
        conversations.end(CallSid)
        return _twiml(response)

    _listen(response)
    return _twiml(response)


def run() -> None:
    """Entry point for the `call-pilot-serve` script."""
    import uvicorn

    uvicorn.run("call_agent.web.app:app", host="0.0.0.0", port=8000, reload=True)
