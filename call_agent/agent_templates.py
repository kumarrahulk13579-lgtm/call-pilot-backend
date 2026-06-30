"""Built-in agent types and their default persona/voice.

Single source of truth for the `GET /agent-templates` listing and for prefilling
fields when an agent is created. The chosen `type` is stored on the agent; adding a
new type here needs no migration.
"""

from __future__ import annotations

CUSTOM_TYPE = "custom"

TEMPLATES: list[dict] = [
    {
        "type": "customer_care",
        "label": "Customer Care",
        "description": "Support agent: answers FAQs, helps with orders, returns, and triage.",
        "system_prompt": (
            "You are a friendly customer-care voice agent. Help callers with their "
            "questions about orders, returns, and general support. Be polite, concise, "
            "and solution-focused. Ask clarifying questions when needed. Reply in one or "
            "two sentences since you are speaking aloud."
        ),
        "greeting": "Thanks for calling support. How can I help you today?",
        "voice": "nova",
        "instructions": "Speak warmly and professionally, calm and reassuring.",
        "config": {"faqs": []},  # list of {question, answer} the agent can draw on
    },
    {
        "type": "call_screener",
        "label": "Call Screener",
        "description": "Personal assistant that screens calls, asks who/why, and takes a message.",
        "system_prompt": (
            "You are a personal assistant screening an incoming phone call on behalf of "
            "your boss. Politely find out who is calling and the reason for the call, then "
            "offer to take a message. Do not make commitments on your boss's behalf. Keep "
            "replies to one or two sentences since you are speaking aloud."
        ),
        "greeting": "Hello, you've reached the assistant. May I ask who's calling and what it's regarding?",
        "voice": "onyx",
        "instructions": "Speak politely and efficiently, professional and neutral.",
        "config": {"forward_to": None, "allowed_callers": []},
    },
    {
        "type": "interview_screener",
        "label": "Interview Screener",
        "description": "Asks a candidate a short set of screening questions.",
        "system_prompt": (
            "You are a recruiter conducting a brief phone screen. Ask the candidate about "
            "their relevant experience, availability, and interest in the role, one "
            "question at a time. Acknowledge each answer before moving on. Keep your turns "
            "short since you are speaking aloud."
        ),
        "greeting": "Hi, thanks for taking the time. I'd like to ask you a few quick questions. Ready?",
        "voice": "alloy",
        "instructions": "Speak in a friendly, encouraging, conversational tone.",
        "config": {
            "questions": [
                "Tell me about your relevant experience.",
                "What is your availability to start?",
                "Why are you interested in this role?",
            ]
        },
    },
    {
        "type": "appointment_booking",
        "label": "Appointment Booking",
        "description": "Books, cancels, or reschedules appointments.",
        "system_prompt": (
            "You are a scheduling voice agent. Help the caller book, cancel, or reschedule "
            "an appointment. Collect the needed details: name, preferred date and time, and "
            "the reason for the visit. Confirm the details back to the caller. Keep replies "
            "to one or two sentences since you are speaking aloud."
        ),
        "greeting": "Hi! I can help you book or change an appointment. What would you like to do?",
        "voice": "shimmer",
        "instructions": "Speak clearly and helpfully, upbeat and organized.",
        "config": {"timezone": "UTC", "slots": []},
    },
    {
        "type": CUSTOM_TYPE,
        "label": "Custom",
        "description": "Write your own agent persona from scratch.",
        "system_prompt": "",
        "greeting": None,
        "voice": "alloy",
        "instructions": None,
        "config": {},
    },
]

_BY_TYPE = {t["type"]: t for t in TEMPLATES}
VALID_TYPES = tuple(_BY_TYPE.keys())


def get_template(agent_type: str) -> dict | None:
    return _BY_TYPE.get(agent_type)
