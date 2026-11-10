"""Retry a model call a couple of times if it looks like a rate limit, not a
real failure — free tiers are expected to hit this sometimes."""
from __future__ import annotations

import re
import time

RATE_LIMIT_PATTERNS = re.compile(
    r"429|rate.?limit|quota|RESOURCE_EXHAUSTED|503|UNAVAILABLE|high demand|overloaded"
    r"|connection error|timeout|timed out",
    re.IGNORECASE,
)

# Matches Google's `'retryDelay': '19618s'` and Groq's "Please try again in
# 2m11.328s" / "in 45.2s" — using the server's own suggested wait, when it
# gives one, beats guessing with a fixed backoff.
_GOOGLE_DELAY = re.compile(r"retryDelay['\"]?\s*:\s*['\"](\d+(?:\.\d+)?)s", re.IGNORECASE)
_HUMAN_DELAY = re.compile(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", re.IGNORECASE)

# Beyond this, the wait is hours away (a real daily reset), not worth
# blocking a thread for — better to give up for this run and let a later
# run pick the chunk back up (everything is saved/resumable already).
LONG_WAIT_THRESHOLD_SECONDS = 600


def extract_retry_delay_seconds(error_text: str) -> float | None:
    m = _GOOGLE_DELAY.search(error_text)
    if m:
        return float(m.group(1))
    m = _HUMAN_DELAY.search(error_text)
    if m:
        minutes = float(m.group(1)) if m.group(1) else 0.0
        return minutes * 60 + float(m.group(2))
    return None


def call_with_retry(caller, prompt: str, max_retries: int = 4, base_delay: float = 25.0) -> dict:
    last_result = None
    for attempt in range(max_retries + 1):
        result = caller(prompt)
        last_result = result
        if result["error"] is None:
            return result
        if not RATE_LIMIT_PATTERNS.search(result["error"]):
            return result  # a real error, not a rate limit — don't retry

        delay = extract_retry_delay_seconds(result["error"])
        if delay is not None and delay > LONG_WAIT_THRESHOLD_SECONDS:
            result["long_wait_seconds"] = delay
            return result  # hours-away reset — don't block this thread

        if attempt < max_retries:
            wait = delay + 2 if delay is not None else base_delay * (attempt + 1)
            print(f"    rate-limited, waiting {wait:.0f}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
    return last_result
