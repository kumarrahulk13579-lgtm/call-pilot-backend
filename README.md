# CallPilot Backend

Python backend for CallPilot, using Azure OpenAI for transcription, chat, and text-to-speech.

## Setup

Create `.env` from `.env.example`, then fill in your Azure OpenAI values:

```txt
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=
AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT=
AZURE_OPENAI_TTS_DEPLOYMENT=
```

Install dependencies:

```powershell
uv sync
```

Validate local environment values:

```powershell
uv run call-pilot-validate-env
```

The direct script also works:

```powershell
uv run python scripts/validate_env.py
```

Run a live Azure model smoke test:

```powershell
uv run call-pilot-smoke-azure
```

## Call agent (Slice 1 — "call and talk")

A simple inbound, turn-based phone agent: a caller talks, the agent listens and
replies out loud, back and forth. Twilio handles speech-to-text and the spoken
voice; Azure OpenAI generates the replies.

Start the server:

```powershell
uv run call-pilot-serve
```

It listens on `http://0.0.0.0:8000` with three routes:

- `GET /health` — health check.
- `POST /voice` — Twilio hits this when a call comes in; returns a greeting and starts listening.
- `POST /respond` — Twilio posts the caller's speech (`SpeechResult`); returns the agent's spoken reply and listens again.

### Test locally (no Twilio needed)

```powershell
# Call begins
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/voice -Method POST

# A caller turn (reuse the same CallSid to keep conversation memory)
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/respond -Method POST `
  -Body @{ CallSid = "TEST123"; SpeechResult = "Hi, who is this?" }
```

Each response is TwiML XML. Saying something with "bye"/"goodbye"/"thank you, bye"
ends the call.

### Test with a real phone call (inbound)

1. Expose the local server: `ngrok http 8000`.
2. In the Twilio console, set the number's Voice "A call comes in" webhook to
   `https://<ngrok-id>.ngrok.io/voice` (HTTP POST).
3. Call the number and talk to the agent.

## Outbound calling (Slice 2)

Place a call *from* the agent. When the person answers, Twilio fetches `/voice`
and the same turn-based talk loop runs — outbound reuses the inbound agent.

Add Twilio values to `.env`:

```txt
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
PUBLIC_BASE_URL=https://<ngrok-id>.ngrok.io
```

Run the server (`uv run call-pilot-serve`) with `ngrok http 8000` pointing at it,
then place a call:

```powershell
uv run call-pilot-call +14155551234
```

It prints the Twilio Call SID. The callee picks up and talks to the agent.
