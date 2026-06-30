from __future__ import annotations

from pathlib import Path
import sys
import traceback

from call_agent.azure_openai import AzureOpenAIClient
from call_agent.config import AzureOpenAIConfig


def main(
    client: AzureOpenAIClient | None = None,
    output_dir: str | Path = "artifacts/smoke",
) -> int:
    if client is None:
        client = AzureOpenAIClient(AzureOpenAIConfig.from_env())

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    audio_path = output_path / "azure-tts-smoke.mp3"

    try:
        print("Testing chat deployment...")
        chat_reply = client.chat("Reply in one short sentence: CallPilot chat is working.")
        print(f"Chat reply: {chat_reply}")

        print("Testing TTS deployment...")
        audio = client.text_to_speech("CallPilot speech test.")
        audio_path.write_bytes(audio)
        print(f"TTS audio saved: {audio_path}")

        print("Testing transcription deployment...")
        transcript = client.transcribe(audio_path)
        print(f"Transcription: {transcript}")
    except Exception as error:
        print(f"{_step_name(error)} failed: {type(error).__name__}")
        return 1

    print("Azure model smoke test complete.")
    return 0


def _step_name(error: Exception) -> str:
    traceback_text = "".join(traceback.format_tb(error.__traceback__))
    if "text_to_speech" in traceback_text:
        return "TTS deployment"
    if "transcribe" in traceback_text:
        return "Transcription deployment"
    if "chat" in traceback_text:
        return "Chat deployment"
    return "Azure smoke test"


if __name__ == "__main__":
    sys.exit(main())
