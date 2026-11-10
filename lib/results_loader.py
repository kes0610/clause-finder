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
