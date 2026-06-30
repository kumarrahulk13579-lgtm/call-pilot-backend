"""Place an outbound call that connects to the same talk agent.

When the person answers, Twilio fetches `{PUBLIC_BASE_URL}/voice` and the normal
turn-based flow runs — outbound reuses the inbound agent unchanged.
"""

from __future__ import annotations

from twilio.rest import Client

from call_agent.config import TwilioConfig


def place_call(to_number: str, config: TwilioConfig | None = None) -> str:
    """Start an outbound call to `to_number`. Returns the Twilio Call SID."""
    config = config or TwilioConfig.from_env()
    client = Client(config.account_sid, config.auth_token)
    call = client.calls.create(
        to=to_number,
        from_=config.from_number,
        url=f"{config.public_base_url}/voice",
    )
    return call.sid
