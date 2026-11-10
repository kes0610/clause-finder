"""Retry a model call a couple of times if it looks like a rate limit, not a
real failure — free tiers are expected to hit this sometimes."""
import re
import time

RATE_LIMIT_PATTERNS = re.compile(
    r"429|rate.?limit|quota|RESOURCE_EXHAUSTED|503|UNAVAILABLE|high demand|overloaded",
    re.IGNORECASE,
)


def call_with_retry(caller, prompt: str, max_retries: int = 2, base_delay: float = 20.0) -> dict:
    last_result = None
    for attempt in range(max_retries + 1):
        result = caller(prompt)
        last_result = result
        if result["error"] is None:
            return result
        if not RATE_LIMIT_PATTERNS.search(result["error"]):
            return result  # a real error, not a rate limit — don't retry
        if attempt < max_retries:
            delay = base_delay * (attempt + 1)
            print(f"    rate-limited, waiting {delay:.0f}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(delay)
    return last_result
