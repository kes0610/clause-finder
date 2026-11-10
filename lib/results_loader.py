"""
Load already-saved Stage 4 results from disk (no API calls) — for the demo
tool's "browse already-analyzed contracts" mode and, later, Stage 5 scoring.
"""
from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

from lib.clause_extraction import CLAUSE_DEFINITIONS, CUAD_COLUMN_NAMES

# Absolute, not relative to whatever the current working directory happens
# to be when this runs (e.g. Streamlit may be launched from a different cwd).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = _PROJECT_ROOT / "data/processed/sample_contracts.csv"
MASTER_CSV = _PROJECT_ROOT / "data/raw/master_clauses.csv"
FULL_RUN_DIR = _PROJECT_ROOT / "data/model_outputs/full_run"

MODEL_LABELS = {
    "gemini_3_5_flash_lite": "Gemini 3.5 Flash-Lite",
    "gemini_3_1_flash_lite": "Gemini 3.1 Flash-Lite",
    "llama_local": "Llama 3.2 (local)",
}


def list_analyzed_contracts() -> list[str]:
    """Document names (not raw filenames) for every contract in the sample, for a picker."""
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row["Filename"] for row in rows]


def list_contracts_for_picker() -> list[tuple[str, str]]:
    """(pdf_filename, short_label) pairs — the raw filenames are long, messy
    SEC-filing names (dates, exhibit codes), so the picker shows the plain
    contract type instead, numbered when the same type repeats."""
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    seen_counts: dict[str, int] = {}
    pairs = []
    for row in rows:
        try:
            parsed = ast.literal_eval(row["Document Name"])
            doc_type = (parsed[0] if parsed else "Untitled").strip().title()
        except (ValueError, SyntaxError):
            doc_type = row["Document Name"].strip().title() or "Untitled"

        seen_counts[doc_type] = seen_counts.get(doc_type, 0) + 1
        label = doc_type if seen_counts[doc_type] == 1 else f"{doc_type} (#{seen_counts[doc_type]})"
        pairs.append((row["Filename"], label))

    return sorted(pairs, key=lambda pair: pair[1])


def merge_saved_results(model_key: str, pdf_filename: str) -> dict:
    """Merge every saved chunk file for one contract + model into one clause dict.

    Mirrors the live tool's merge logic exactly, just reading from disk
    instead of calling the model.
    """
    contract_stem = pdf_filename.rsplit(".", 1)[0]
    model_dir = FULL_RUN_DIR / model_key
    merged = {key: {"present": False, "quote": None} for key in CLAUSE_DEFINITIONS}
    chunk_files = sorted(model_dir.glob(f"{contract_stem}_chunk*.json")) if model_dir.exists() else []

    found_error = False
    for path in chunk_files:
        record = json.loads(path.read_text())
        if record.get("error"):
            found_error = True
            continue
        parsed = record.get("parsed_json")
        if parsed:
            for clause_key, info in parsed.items():
                if clause_key in merged and info.get("present") and not merged[clause_key]["present"]:
                    merged[clause_key] = {"present": True, "quote": info.get("quote")}

    return {
        "clauses": merged,
        "chunks_found": len(chunk_files),
        "had_error": found_error,
    }


_ground_truth_cache: dict | None = None


def _load_ground_truth_csv() -> dict:
    global _ground_truth_cache
    if _ground_truth_cache is None:
        _ground_truth_cache = {}
        if MASTER_CSV.exists():
            with open(MASTER_CSV, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    _ground_truth_cache[row["Filename"]] = row
    return _ground_truth_cache


def compute_sample_clause_counts() -> dict[str, int]:
    """How many of the 130 sampled contracts actually have each clause type (ground truth)."""
    counts = {key: 0 for key in CLAUSE_DEFINITIONS}
    for filename in list_analyzed_contracts():
        truth = get_ground_truth(filename)
        if truth:
            for key, info in truth.items():
                if info["present"]:
                    counts[key] += 1
    return counts


def compute_model_progress(model_key: str) -> dict:
    """How many of the 130 contracts have a complete, error-free saved result."""
    contracts = list_analyzed_contracts()
    complete, incomplete = 0, 0
    for filename in contracts:
        outcome = merge_saved_results(model_key, filename)
        if outcome["chunks_found"] > 0 and not outcome["had_error"]:
            complete += 1
        else:
            incomplete += 1
    return {"complete": complete, "incomplete": incomplete, "total": len(contracts)}


def compute_preliminary_scores(model_key: str) -> dict[str, dict]:
    """Rough precision/recall per clause type, only over contracts with a
    complete saved result for this model. Preliminary — not the final,
    statistically-rigorous Stage 5 scoring (no confidence intervals here)."""
    tally = {key: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for key in CLAUSE_DEFINITIONS}
    contracts_used = 0

    for filename in list_analyzed_contracts():
        outcome = merge_saved_results(model_key, filename)
        if outcome["chunks_found"] == 0 or outcome["had_error"]:
            continue
        truth = get_ground_truth(filename)
        if truth is None:
            continue
        contracts_used += 1
        for key in CLAUSE_DEFINITIONS:
            predicted = outcome["clauses"][key]["present"]
            actual = truth[key]["present"]
            if predicted and actual:
                tally[key]["tp"] += 1
            elif predicted and not actual:
                tally[key]["fp"] += 1
            elif not predicted and actual:
                tally[key]["fn"] += 1
            else:
                tally[key]["tn"] += 1

    scores = {}
    for key, t in tally.items():
        precision = t["tp"] / (t["tp"] + t["fp"]) if (t["tp"] + t["fp"]) > 0 else None
        recall = t["tp"] / (t["tp"] + t["fn"]) if (t["tp"] + t["fn"]) > 0 else None
        scores[key] = {**t, "precision": precision, "recall": recall}
    return {"contracts_used": contracts_used, "clauses": scores}


def get_ground_truth(pdf_filename: str) -> dict | None:
    """The lawyer's real answer for each clause type, straight from CUAD's own labels."""
    rows = _load_ground_truth_csv()
    row = rows.get(pdf_filename)
    if row is None:
        return None

    result = {}
    for clause_key, column in CUAD_COLUMN_NAMES.items():
        raw = row.get(column, "[]")
        present = raw not in ("[]", "", None)
        quote = None
        if present:
            try:
                quotes = ast.literal_eval(raw)
                quote = quotes[0] if quotes else None
            except (ValueError, SyntaxError):
                quote = raw
        result[clause_key] = {"present": present, "quote": quote}
    return result
