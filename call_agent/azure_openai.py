from __future__ import annotations

from pathlib import Path
import requests

from call_agent.config import AzureOpenAIConfig


class AzureOpenAIClient:
    def __init__(
        self,
        config: AzureOpenAIConfig,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.endpoint = config.endpoint.rstrip("/")
        self.session = session or requests.Session()

    def chat(self, prompt: str) -> str:
        response = self.session.post(
            self._url(self.config.chat_deployment, "chat/completions"),
            headers=self._json_headers(),
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise AI call agent.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 120,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def chat_messages(
        self,
        messages: list[dict],
        max_tokens: int = 200,
        temperature: float = 0.2,
    ) -> str:
        response = self.session.post(
            self._url(self.config.chat_deployment, "chat/completions"),
            headers=self._json_headers(),
            json={
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def text_to_speech(
        self,
        text: str,
        voice: str = "alloy",
        response_format: str = "mp3",
        instructions: str | None = None,
    ) -> bytes:
        payload = {
            "model": self.config.tts_deployment,
            "input": text,
            "voice": voice,
            "response_format": response_format,
        }
        if instructions:
            payload["instructions"] = instructions  # steers tone/accent (gpt-4o-mini-tts)
        response = self.session.post(
            self._url(self.config.tts_deployment, "audio/speech"),
            headers=self._json_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text (batch request)."""
        if not self.config.embed_deployment:
            raise RuntimeError(
                "AZURE_OPENAI_EMBED_DEPLOYMENT is not set; embeddings are required for RAG."
            )
        response = self.session.post(
            self._url(self.config.embed_deployment, "embeddings"),
            headers=self._json_headers(),
            json={"model": self.config.embed_deployment, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    def transcribe(self, audio_path: str | Path) -> str:
        path = Path(audio_path)
        with path.open("rb") as audio_file:
            response = self.session.post(
                self._url(self.config.transcribe_deployment, "audio/transcriptions"),
                headers=self._auth_headers(),
                data={"model": self.config.transcribe_deployment},
                files={"file": (str(path), audio_file, _content_type(path))},
                timeout=60,
            )
        response.raise_for_status()
        data = response.json()
        return data["text"]

    def _url(self, deployment: str, path: str) -> str:
        return (
            f"{self.endpoint}/openai/deployments/{deployment}/{path}"
            f"?api-version={self.config.api_version}"
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"api-key": self.config.api_key}

    def _json_headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}


def _content_type(path: Path) -> str:
    content_types: dict[str, str] = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }
    return content_types.get(path.suffix.lower(), "application/octet-stream")
