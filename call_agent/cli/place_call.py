"""CLI to place an outbound call: `call-pilot-call <to-number>`."""

from __future__ import annotations

import sys

from call_agent.outbound import place_call


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: call-pilot-call <to-number>  (E.164, e.g. +14155551234)")
        return 2

    try:
        call_sid = place_call(argv[0])
    except Exception as error:
        print(f"Failed to place call: {type(error).__name__}: {error}")
        return 1

    print(f"Call placed. Call SID: {call_sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
