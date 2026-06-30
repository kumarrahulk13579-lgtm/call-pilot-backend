from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    api_version: str
    chat_deployment: str
    transcribe_deployment: str
    tts_deployment: str
    embed_deployment: str = ""  # optional; only needed for RAG retrieval

    @classmethod
    def required_env_vars(cls) -> tuple[str, ...]:
        return (
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_CHAT_DEPLOYMENT",
            "AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT",
            "AZURE_OPENAI_TTS_DEPLOYMENT",
        )

    @classmethod
    def from_env(cls, load_dotenv_file: bool = True) -> "AzureOpenAIConfig":
        if load_dotenv_file:
            _load_dotenv_if_available()

        values = {name: os.getenv(name, "").strip() for name in cls.required_env_vars()}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        return cls(
            endpoint=values["AZURE_OPENAI_ENDPOINT"].rstrip("/"),
            api_key=values["AZURE_OPENAI_API_KEY"],
            api_version=values["AZURE_OPENAI_API_VERSION"],
            chat_deployment=values["AZURE_OPENAI_CHAT_DEPLOYMENT"],
            transcribe_deployment=values["AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT"],
            tts_deployment=values["AZURE_OPENAI_TTS_DEPLOYMENT"],
            embed_deployment=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "").strip(),
        )


@dataclass(frozen=True)
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_number: str
    public_base_url: str

    @classmethod
    def required_env_vars(cls) -> tuple[str, ...]:
        return (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_FROM_NUMBER",
            "PUBLIC_BASE_URL",
        )

    @classmethod
    def from_env(cls, load_dotenv_file: bool = True) -> "TwilioConfig":
        if load_dotenv_file:
            _load_dotenv_if_available()

        values = {name: os.getenv(name, "").strip() for name in cls.required_env_vars()}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        return cls(
            account_sid=values["TWILIO_ACCOUNT_SID"],
            auth_token=values["TWILIO_AUTH_TOKEN"],
            from_number=values["TWILIO_FROM_NUMBER"],
            public_base_url=values["PUBLIC_BASE_URL"].rstrip("/"),
        )


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()
