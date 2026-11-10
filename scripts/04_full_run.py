"""
Stage 4: the real run — all 130 sampled contracts, through each model.

Only the 4 free models run here (Claude is added separately later, once
these results look solid, per the plan). Runs the 4 models in parallel
threads (each model is otherwise sequential within itself, pacing against
its own rate limit) so the wall-clock time is roughly the slowest model's
time, not the sum of all four.

Resumable by design: every chunk's result is saved as its own file, and a
re-run skips any chunk that already has a successful saved result. So if
this crashes, hits a daily quota wall, or is simply stopped, running it
again later picks up exactly where it left off — nothing is redone, nothing
is lost.
"""
from __future__ import annotations

import csv
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.clause_extraction import build_prompt, chunk_contract, count_tokens
from lib.model_clients import CALLERS
from lib.retry import call_with_retry

SAMPLE_CSV = "data/processed/sample_contracts.csv"
CONTRACT_DIR = Path("data/raw/full_contract_txt")
OUT_DIR = Path("data/model_outputs/full_run")

# Claude is deliberately excluded here — added separately once these are
# confirmed solid, since it's the one paid model. Groq's gpt-oss-120b was
# dropped: its hidden "reasoning" tokens blew through Groq's 200K
# tokens/day free cap so fast the full run would've taken ~a month. The
# only other free, non-reasoning Groq model was Alibaba's Qwen, which the
# author wasn't comfortable sending contract text to — a legitimate
# vendor-trust call, not a technical one, and worth noting in the memo.
MODELS_TO_RUN = ["gemini_3_5_flash_lite", "gemini_3_1_flash_lite", "llama_local"]

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def extract_json(text: str | None) -> dict | None:
    if text is None:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]
    for extra_braces in ("", "}", "}}", "}}}"):
        try:
            return json.loads(cleaned + extra_braces)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def load_contracts() -> list[str]:
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row["Filename"].rsplit(".", 1)[0] + ".txt" for row in rows]


def run_model(model_name: str, contracts: list[str]) -> dict:
    caller = CALLERS[model_name]
    model_dir = OUT_DIR / model_name
    model_dir.mkdir(parents=True, exist_ok=True)

    stats = {"done": 0, "skipped_already_done": 0, "parse_ok": 0, "parse_fail": 0,
              "errors": 0, "stopped_early": False, "stop_reason": None}

    for contract_file in contracts:
        if stats["stopped_early"]:
            break
        text = (CONTRACT_DIR / contract_file).read_text(encoding="utf-8", errors="replace")
        chunks = chunk_contract(text)
        contract_stem = contract_file.rsplit(".", 1)[0]

        for i, chunk in enumerate(chunks, 1):
            out_path = model_dir / f"{contract_stem}_chunk{i}of{len(chunks)}.json"
            if out_path.exists():
                existing = json.loads(out_path.read_text())
                if existing.get("error") is None:
                    stats["skipped_already_done"] += 1
                    continue

            prompt = build_prompt(chunk)
            result = call_with_retry(caller, prompt)
            parsed = extract_json(result["text"])

            record = {
                "model": model_name,
                "contract_file": contract_file,
                "chunk_index": i,
                "chunk_total": len(chunks),
                "chunk_input_tokens_est": count_tokens(chunk),
                "prompt_input_tokens_reported": result["input_tokens"],
                "output_tokens_reported": result["output_tokens"],
                "latency_seconds": result["latency_seconds"],
                "error": result["error"],
                "raw_response": result["text"],
                "parsed_ok": parsed is not None,
                "parsed_json": parsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            out_path.write_text(json.dumps(record, indent=2))

            stats["done"] += 1
            if result["error"]:
                stats["errors"] += 1
                log(f"[{model_name}] {contract_file[:40]:40s} chunk {i}/{len(chunks)}  ERROR: {result['error'][:90]}")
                if result.get("long_wait_seconds"):
                    stats["stopped_early"] = True
                    stats["stop_reason"] = f"{result['long_wait_seconds']:.0f}s wait needed: {result['error'][:150]}"
                    log(f"[{model_name}] *** needs a {result['long_wait_seconds']/60:.0f}-minute+ wait — "
                        f"stopping this model, resume later ***")
                    break
            else:
                if parsed is not None:
                    stats["parse_ok"] += 1
                else:
                    stats["parse_fail"] += 1

        if stats["done"] % 20 == 0 and stats["done"] > 0:
            log(f"[{model_name}] progress: {stats['done']} new chunks done so far")

    return stats


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contracts = load_contracts()
    log(f"Full run: {len(contracts)} contracts x {len(MODELS_TO_RUN)} models")
    log(f"Models: {MODELS_TO_RUN}\n")

    start = time.monotonic()
    results = {}
    with ThreadPoolExecutor(max_workers=len(MODELS_TO_RUN)) as pool:
        futures = {pool.submit(run_model, name, contracts): name for name in MODELS_TO_RUN}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"crashed": str(e)}
                log(f"[{name}] CRASHED: {e}")

    elapsed = time.monotonic() - start
    log(f"\n=== Full run finished in {elapsed/60:.1f} minutes ===")
    for name, s in results.items():
        log(f"{name}: {s}")

    summary_path = OUT_DIR / "_summary.json"
    summary_path.write_text(json.dumps({"results": results, "elapsed_seconds": elapsed}, indent=2))
    log(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
