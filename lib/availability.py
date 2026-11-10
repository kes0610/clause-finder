"""
Check whether a model is actually usable right now, with one trivial live
test call — there's no API to just ask a provider "how much free quota do I
have left," so a cheap real call is the only reliable way to know before
committing to a real run.
"""
from __future__ import annotations

from lib.model_clients import CALLERS
from lib.retry import extract_retry_delay_seconds

_TEST_PROMPT = "Reply with exactly one word: ready"


def check_availability(model_key: str) -> dict:
    result = CALLERS[model_key](_TEST_PROMPT)
    if result["error"] is None:
        return {"available": True, "wait_seconds": None, "error": None}

    wait_seconds = extract_retry_delay_seconds(result["error"])
    return {"available": False, "wait_seconds": wait_seconds, "error": result["error"][:200]}
