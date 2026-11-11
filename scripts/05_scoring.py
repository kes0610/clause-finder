"""
Stage 5: the real scoring — precision, recall, and F1 for every model on
every clause type, with 95% confidence intervals from bootstrap resampling
(not just the single-number "preliminary" estimates from Stage 4).

Why bootstrap: with only 130 contracts, a single precision/recall number
could look different on a different sample of 130 real-world contracts.
Bootstrapping estimates how much it could plausibly wobble by resampling
the 130 contracts (with replacement) thousands of times and recomputing the
score each time — the middle 95% of those recomputed scores is the
confidence interval.

Also flags failure patterns: clause types where models systematically
over-flag (many false positives) or under-flag (many false negatives), and
whether a clause type's errors cluster on a few contracts or spread evenly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from lib.clause_extraction import CLAUSE_DEFINITIONS
from lib.results_loader import get_ground_truth, list_analyzed_contracts, merge_saved_results

MODELS = {
    "gemini_3_5_flash_lite": "Gemini 3.5 Flash-Lite",
    "gemini_3_1_flash_lite": "Gemini 3.1 Flash-Lite",
    "llama_local": "Llama 3.2 (local)",
    "claude_sonnet": "Claude Sonnet 5.5",
}

N_BOOTSTRAP = 10_000
RNG_SEED = 42  # same seed used for the original contract sample, for consistency
CI_LOW, CI_HIGH = 2.5, 97.5  # percentiles for a 95% confidence interval

OUT_PATH = Path("data/model_outputs/stage5_scoring.json")


def load_predictions_and_truth(model_key: str, contracts: list[str]) -> dict:
    """Per clause type: parallel arrays of (predicted, actual) booleans, one
    entry per contract, in the same contract order for every clause type."""
    per_clause = {key: {"predicted": [], "actual": []} for key in CLAUSE_DEFINITIONS}
    for filename in contracts:
        outcome = merge_saved_results(model_key, filename)
        truth = get_ground_truth(filename)
        if truth is None:
            continue
        for key in CLAUSE_DEFINITIONS:
            per_clause[key]["predicted"].append(outcome["clauses"][key]["present"])
            per_clause[key]["actual"].append(truth[key]["present"])
    return per_clause


def precision_recall_f1(predicted: np.ndarray, actual: np.ndarray) -> dict:
    tp = int(np.sum(predicted & actual))
    fp = int(np.sum(predicted & ~actual))
    fn = int(np.sum(~predicted & actual))
    tn = int(np.sum(~predicted & ~actual))
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and (precision + recall) > 0
          else None)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def bootstrap_ci(predicted: np.ndarray, actual: np.ndarray, rng: np.random.Generator) -> dict:
    """Resample contracts with replacement N_BOOTSTRAP times; return the 95%
    CI for precision, recall, and F1 (None where undefined too often to say)."""
    n = len(predicted)
    samples = {"precision": [], "recall": [], "f1": []}

    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, size=n)
        scores = precision_recall_f1(predicted[idx], actual[idx])
        for metric in samples:
            if scores[metric] is not None:
                samples[metric].append(scores[metric])

    ci = {}
    for metric, values in samples.items():
        if len(values) < N_BOOTSTRAP * 0.5:
            # undefined (e.g. no predicted-positive contracts) in over half
            # the resamples — too unstable to report a meaningful interval
            ci[metric] = None
        else:
            ci[metric] = (float(np.percentile(values, CI_LOW)),
                          float(np.percentile(values, CI_HIGH)))
    return ci


def main() -> None:
    contracts = list_analyzed_contracts()
    rng = np.random.default_rng(RNG_SEED)
    results = {}

    for model_key, model_label in MODELS.items():
        print(f"Scoring {model_label}...")
        per_clause = load_predictions_and_truth(model_key, contracts)
        results[model_key] = {"label": model_label, "clauses": {}}

        for clause_key in CLAUSE_DEFINITIONS:
            predicted = np.array(per_clause[clause_key]["predicted"])
            actual = np.array(per_clause[clause_key]["actual"])
            point = precision_recall_f1(predicted, actual)
            ci = bootstrap_ci(predicted, actual, rng)
            results[model_key]["clauses"][clause_key] = {**point, "ci_95": ci}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nSaved to {OUT_PATH}")

    # Failure pattern check: for each clause type, how concentrated are a
    # model's false positives/negatives across contracts vs. spread evenly?
    print("\n--- Failure pattern notes ---")
    for model_key, model_label in MODELS.items():
        per_clause = load_predictions_and_truth(model_key, contracts)
        for clause_key in CLAUSE_DEFINITIONS:
            r = results[model_key]["clauses"][clause_key]
            if r["precision"] is not None and r["precision"] < 0.6 and r["fp"] >= 5:
                print(f"{model_label} / {clause_key}: over-flags "
                      f"({r['fp']} false positives, precision {r['precision']:.0%})")
            if r["recall"] is not None and r["recall"] < 0.6 and r["fn"] >= 5:
                print(f"{model_label} / {clause_key}: under-flags "
                      f"({r['fn']} false negatives, recall {r['recall']:.0%})")


if __name__ == "__main__":
    main()
