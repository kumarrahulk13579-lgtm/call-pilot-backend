"""In-memory, per-call conversation handling for the simple call agent."""

from __future__ import annotations

from call_agent.azure_openai import AzureOpenAIClient

SYSTEM_PROMPT = (
    "You are a friendly AI voice agent on a phone call. "
    "Keep replies short and natural, since they are spoken aloud. "
    "Answer in one or two sentences. Do not use lists, markdown, or emojis."
)


class ConversationStore:
    """Holds the running message list for each active call, keyed by CallSid."""

    def __init__(self, client: AzureOpenAIClient) -> None:
        self._client = client
        self._calls: dict[str, list[dict]] = {}

    def generate_reply(self, call_sid: str, user_text: str) -> str:
        messages = self._calls.setdefault(
            call_sid, [{"role": "system", "content": SYSTEM_PROMPT}]
        )
        messages.append({"role": "user", "content": user_text})
        reply = self._client.chat_messages(messages)
        messages.append({"role": "assistant", "content": reply})
        return reply

    def end(self, call_sid: str) -> None:
        self._calls.pop(call_sid, None)
