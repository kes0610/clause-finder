"""
One small wrapper per model, all returning the same shape, so the rest of
the project doesn't need to care which provider it's talking to.

Every call_* function returns a dict:
    {
        "text": str | None,       # the model's raw reply
        "input_tokens": int | None,
        "output_tokens": int | None,
        "latency_seconds": float,
        "error": str | None,      # set instead of "text" if the call failed
    }
"""
import os
import time

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

MODEL_IDS = {
    # Gemini 3.8 Flash was dropped during the Stage 3 pilot: its free tier
    # turned out to allow only 20 requests/day, discovered via a live 429
    # error (not published in Google's docs) — too low for this project's
    # request volume. Both Flash-Lite tiers below ran fine in the pilot.
    "gemini_3_5_flash_lite": "gemini-3.5-flash-lite",
    "gemini_3_1_flash_lite": "gemini-3.1-flash-lite",
    "groq_gpt_oss": "openai/gpt-oss-120b",
    "llama_local": "llama3.2",
    "claude_sonnet": "claude-sonnet-5-5",
}

_google_client = None
_groq_client = None
_anthropic_client = None


def _timed(fn):
    start = time.monotonic()
    result = fn()
    result["latency_seconds"] = round(time.monotonic() - start, 2)
    return result


def call_gemini(prompt: str, model_key: str = "gemini_3_5_flash_lite") -> dict:
    global _google_client
    if _google_client is None:
        _google_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def run():
        try:
            resp = _google_client.models.generate_content(
                model=MODEL_IDS[model_key], contents=prompt,
            )
            usage = resp.usage_metadata
            return {
                "text": resp.text,
                "input_tokens": usage.prompt_token_count if usage else None,
                "output_tokens": usage.candidates_token_count if usage else None,
                "error": None,
            }
        except Exception as e:
            return {"text": None, "input_tokens": None, "output_tokens": None, "error": str(e)}

    return _timed(run)


def call_groq(prompt: str) -> dict:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def run():
        try:
            resp = _groq_client.chat.completions.create(
                model=MODEL_IDS["groq_gpt_oss"],
                messages=[{"role": "user", "content": prompt}],
            )
            usage = resp.usage
            return {
                "text": resp.choices[0].message.content,
                "input_tokens": usage.prompt_tokens if usage else None,
                "output_tokens": usage.completion_tokens if usage else None,
                "error": None,
            }
        except Exception as e:
            return {"text": None, "input_tokens": None, "output_tokens": None, "error": str(e)}

    return _timed(run)


def call_claude(prompt: str) -> dict:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def run():
        try:
            resp = _anthropic_client.messages.create(
                model=MODEL_IDS["claude_sonnet"],
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            # Sonnet 5.5 can return a ThinkingBlock before the actual
            # TextBlock reply — the pilot caught `.content[0].text`
            # crashing on those, so find the real text block instead.
            text_blocks = [b.text for b in resp.content if b.type == "text"]
            return {
                "text": text_blocks[0] if text_blocks else None,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "error": None,
            }
        except Exception as e:
            return {"text": None, "input_tokens": None, "output_tokens": None, "error": str(e)}

    return _timed(run)


def call_llama_local(prompt: str) -> dict:
    def run():
        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": MODEL_IDS["llama_local"],
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    # Ollama defaults to a 2048-token context window. The
                    # pilot showed 4096 still truncates output mid-JSON on
                    # chunks with several long quotes — input (~3700 tokens
                    # worst case) plus output need more headroom.
                    "options": {"num_ctx": 8192},
                },
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "text": data.get("message", {}).get("content"),
                "input_tokens": data.get("prompt_eval_count"),
                "output_tokens": data.get("eval_count"),
                "error": None,
            }
        except Exception as e:
            return {"text": None, "input_tokens": None, "output_tokens": None, "error": str(e)}

    return _timed(run)


CALLERS = {
    "gemini_3_5_flash_lite": lambda p: call_gemini(p, "gemini_3_5_flash_lite"),
    "gemini_3_1_flash_lite": lambda p: call_gemini(p, "gemini_3_1_flash_lite"),
    "groq_gpt_oss": call_groq,
    "llama_local": call_llama_local,
    "claude_sonnet": call_claude,
}
