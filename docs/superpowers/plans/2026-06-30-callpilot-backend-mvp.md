# CallPilot Backend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable CallPilot backend API around the verified Azure OpenAI chat, transcription, and text-to-speech deployments.

**Architecture:** Keep Azure provider code isolated in `call_agent/azure_openai.py` and expose it through a small FastAPI application. The backend starts with stateless endpoints first; database, auth, call logs, and admin UI come later.

**Tech Stack:** Python via `uv`, FastAPI, Pydantic, requests, Azure OpenAI REST endpoints.

---

## File Structure

- Modify `pyproject.toml`: add FastAPI runtime dependencies.
- Create `call_agent/app.py`: FastAPI app factory and app instance.
- Create `call_agent/api/__init__.py`: API package marker.
- Create `call_agent/api/routes.py`: health, agent reply, transcription, and speech endpoints.
- Create `call_agent/schemas.py`: request and response models.
- Modify `README.md`: add local API run commands and endpoint examples.

## Task 1: Add FastAPI Runtime Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] Add FastAPI dependencies:

```toml
dependencies = [
    "fastapi==0.115.6",
    "python-dotenv==1.0.1",
    "python-multipart==0.0.20",
    "requests==2.32.3",
    "uvicorn[standard]==0.32.1",
]
```

- [ ] Sync dependencies:

```powershell
uv sync
```

- [ ] Confirm existing Azure validation still works:

```powershell
uv run call-pilot-validate-env
uv run call-pilot-smoke-azure
```

## Task 2: Create FastAPI App And Health Route

**Files:**
- Create: `call_agent/app.py`
- Create: `call_agent/api/__init__.py`
- Create: `call_agent/api/routes.py`

- [ ] Create `call_agent/api/__init__.py`:

```python
"""HTTP API package."""
```

- [ ] Create `call_agent/api/routes.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "call-pilot-backend"}
```

- [ ] Create `call_agent/app.py`:

```python
from fastapi import FastAPI

from call_agent.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="CallPilot Backend")
    app.include_router(router)
    return app


app = create_app()
```

- [ ] Start the API:

```powershell
uv run uvicorn call_agent.app:app --reload
```

- [ ] Check health in a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```txt
status service
------ -------
ok     call-pilot-backend
```

## Task 3: Add Agent Reply Endpoint

**Files:**
- Create: `call_agent/schemas.py`
- Modify: `call_agent/api/routes.py`

- [ ] Create `call_agent/schemas.py`:

```python
from pydantic import BaseModel, Field


class AgentReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentReplyResponse(BaseModel):
    reply: str
```

- [ ] Replace `call_agent/api/routes.py` with:

```python
from fastapi import APIRouter, Depends

from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig
from call_agent.schemas import AgentReplyRequest, AgentReplyResponse

router = APIRouter()


def get_azure_client() -> AzureOpenAIClient:
    return AzureOpenAIClient(AzureOpenAIConfig.from_env())


@router.get("/health")
def health():
    return {"status": "ok", "service": "call-pilot-backend"}


@router.post("/v1/agent/reply", response_model=AgentReplyResponse)
def agent_reply(
    request: AgentReplyRequest,
    azure_client: AzureOpenAIClient = Depends(get_azure_client),
):
    return AgentReplyResponse(reply=azure_client.chat(request.message))
```

- [ ] Manually check the endpoint with the server running:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/agent/reply `
  -ContentType "application/json" `
  -Body '{"message":"Say hello as CallPilot."}'
```

Expected: JSON with a `reply` field.

## Task 4: Add Text-To-Speech Endpoint

**Files:**
- Modify: `call_agent/schemas.py`
- Modify: `call_agent/api/routes.py`

- [ ] Add speech schema to `call_agent/schemas.py`:

```python

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
```

- [ ] Update imports in `call_agent/api/routes.py`:

```python
from fastapi import APIRouter, Depends, Response
from call_agent.schemas import AgentReplyRequest, AgentReplyResponse, SpeechRequest
```

- [ ] Add route to `call_agent/api/routes.py`:

```python

@router.post("/v1/audio/speech")
def text_to_speech(
    request: SpeechRequest,
    azure_client: AzureOpenAIClient = Depends(get_azure_client),
):
    audio = azure_client.text_to_speech(request.text)
    return Response(content=audio, media_type="audio/mpeg")
```

- [ ] Manually check the endpoint with the server running:

```powershell
Invoke-WebRequest `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/audio/speech `
  -ContentType "application/json" `
  -Body '{"text":"CallPilot speech test."}' `
  -OutFile artifacts\manual-api-speech.mp3
```

Expected: `artifacts\manual-api-speech.mp3` is created and playable.

## Task 5: Add Transcription Endpoint

**Files:**
- Modify: `call_agent/schemas.py`
- Modify: `call_agent/api/routes.py`

- [ ] Add transcription schema to `call_agent/schemas.py`:

```python

class TranscriptionResponse(BaseModel):
    text: str
```

- [ ] Update imports in `call_agent/api/routes.py`:

```python
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Response, UploadFile
from call_agent.schemas import (
    AgentReplyRequest,
    AgentReplyResponse,
    SpeechRequest,
    TranscriptionResponse,
)
```

- [ ] Add route to `call_agent/api/routes.py`:

```python

@router.post("/v1/audio/transcriptions", response_model=TranscriptionResponse)
def transcribe_audio(
    file: UploadFile = File(...),
    azure_client: AzureOpenAIClient = Depends(get_azure_client),
):
    suffix = Path(file.filename or "upload.wav").suffix or ".wav"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(file.file.read())

    try:
        text = azure_client.transcribe(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return TranscriptionResponse(text=text)
```

- [ ] Manually check the endpoint with the server running:

```powershell
curl.exe -X POST `
  "http://127.0.0.1:8000/v1/audio/transcriptions" `
  -F "file=@artifacts\manual-api-speech.mp3"
```

Expected: JSON with a `text` field.

## Task 6: Add Provider Error Mapping

**Files:**
- Modify: `call_agent/api/routes.py`

- [ ] Add helper imports:

```python
from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

T = TypeVar("T")
```

- [ ] Add provider-call helper:

```python

def run_provider_call(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Azure OpenAI request failed",
        ) from error
```

- [ ] Wrap provider calls:

```python
return AgentReplyResponse(reply=run_provider_call(lambda: azure_client.chat(request.message)))
```

```python
audio = run_provider_call(lambda: azure_client.text_to_speech(request.text))
```

```python
text = run_provider_call(lambda: azure_client.transcribe(temp_path))
```

- [ ] Manually verify an invalid deployment name in `.env` returns HTTP 502, then restore the correct value and rerun:

```powershell
uv run call-pilot-smoke-azure
```

Expected: the smoke command succeeds after restoring `.env`.

## Task 7: Document API Usage

**Files:**
- Modify: `README.md`

- [ ] Add API run section:

```markdown

## Run API

Start the backend locally:

```powershell
uv run uvicorn call_agent.app:app --reload
```

Open:

```txt
http://127.0.0.1:8000/docs
```

Useful endpoints:

- `GET /health`
- `POST /v1/agent/reply`
- `POST /v1/audio/speech`
- `POST /v1/audio/transcriptions`
```

- [ ] Final manual checks:

```powershell
uv sync
uv run call-pilot-validate-env
uv run call-pilot-smoke-azure
```

Expected: env validation succeeds and Azure smoke test completes.

## Self-Review

- Scope: This plan implements only the stateless backend API layer. It intentionally excludes database, auth, call logs, admin UI, and phone integration.
- Planning-marker scan: No unresolved markers remain.
- Type consistency: Route names, schemas, and dependency names are consistent across tasks.
