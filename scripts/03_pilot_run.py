"""
Stage 3: run the shared prompt against 5 contracts, on all 5 models, and
save every raw response to disk — so we can check the output actually
parses as JSON, see real token counts, and estimate how long/expensive the
full 130-contract run would be, before committing to it.
"""
from __future__ import annotations  # lets `dict | None` type hints work on Python 3.9

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.clause_extraction import build_prompt, chunk_contract, count_tokens, CLAUSE_DEFINITIONS
from lib.model_clients import CALLERS
from lib.retry import call_with_retry

SAMPLE_CSV = "data/processed/sample_contracts.csv"
CONTRACT_DIR = Path("data/raw/full_contract_txt")
OUT_DIR = Path("data/model_outputs/pilot")  # our own outputs — kept/committed, unlike data/raw/
PILOT_SIZE = 5


def extract_json(text: str) -> dict | None:
    """Model replies sometimes wrap JSON in ```json ... ``` fences — strip those first."""
    if text is None:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass
    # Smaller models sometimes forget the final closing brace(s) — a cheap,
    # safe repair attempt before giving up on the whole response.
    for extra_braces in ("}", "}}", "}}}"):
        try:
            return json.loads(cleaned + extra_braces)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def load_pilot_contracts() -> list[str]:
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    filenames = [row["Filename"].rsplit(".", 1)[0] + ".txt" for row in rows]
    return filenames[:PILOT_SIZE]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contracts = load_pilot_contracts()
    print(f"Pilot contracts ({len(contracts)}): {contracts}\n")

    stats = {model: {"requests": 0, "parse_ok": 0, "parse_fail": 0, "errors": 0,
                      "input_tokens": 0, "output_tokens": 0, "total_latency": 0.0}
              for model in CALLERS}

    overall_start = time.monotonic()

    for contract_file in contracts:
        text = (CONTRACT_DIR / contract_file).read_text(encoding="utf-8", errors="replace")
        chunks = chunk_contract(text)
        print(f"=== {contract_file} ({count_tokens(text)} tokens, {len(chunks)} chunk(s)) ===")

        for model_name, caller in CALLERS.items():
            model_dir = OUT_DIR / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            contract_stem = contract_file.rsplit(".", 1)[0]

            for i, chunk in enumerate(chunks, 1):
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
                out_path = model_dir / f"{contract_stem}_chunk{i}of{len(chunks)}.json"
                out_path.write_text(json.dumps(record, indent=2))

                s = stats[model_name]
                s["requests"] += 1
                s["total_latency"] += result["latency_seconds"]
                if result["error"]:
                    s["errors"] += 1
                    print(f"  {model_name:22s} chunk {i}/{len(chunks)}  ERROR: {result['error'][:100]}")
                else:
                    s["input_tokens"] += result["input_tokens"] or 0
                    s["output_tokens"] += result["output_tokens"] or 0
                    if parsed is not None:
                        s["parse_ok"] += 1
                    else:
                        s["parse_fail"] += 1
                    mark = "parsed" if parsed is not None else "DID NOT PARSE"
                    print(f"  {model_name:22s} chunk {i}/{len(chunks)}  {result['latency_seconds']:6.2f}s  {mark}")
        print()

    elapsed = time.monotonic() - overall_start
    print(f"\n=== Pilot summary ({elapsed/60:.1f} minutes total) ===")
    print(f"{'model':22s} {'reqs':>5s} {'parse_ok':>9s} {'parse_fail':>10s} {'errors':>7s} "
          f"{'in_tok':>8s} {'out_tok':>8s} {'avg_sec':>8s}")
    for model, s in stats.items():
        avg_sec = s["total_latency"] / s["requests"] if s["requests"] else 0
        print(f"{model:22s} {s['requests']:5d} {s['parse_ok']:9d} {s['parse_fail']:10d} {s['errors']:7d} "
              f"{s['input_tokens']:8d} {s['output_tokens']:8d} {avg_sec:8.2f}")

    summary_path = OUT_DIR / "_summary.json"
    summary_path.write_text(json.dumps({"stats": stats, "elapsed_seconds": elapsed}, indent=2))
    print(f"\nFull details saved under {OUT_DIR}/, summary at {summary_path}")


if __name__ == "__main__":
    main()
