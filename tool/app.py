"""
Interactive tool for exploring the contract review evaluation — paste in a
brand-new contract and run it live, browse the real 130-contract results
already produced by the full evaluation compared against the lawyers' real
answers, or view a project summary.

Reuses the exact same prompt/chunking/model-calling code as the real
evaluation (lib/), so this isn't a separate, unvalidated code path — it's
the same logic the scored results came from.

Run with: streamlit run tool/app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from pypdf import PdfReader

from lib.clause_extraction import CLAUSE_DEFINITIONS, build_prompt, chunk_contract
from lib.model_clients import CALLERS
from lib.results_loader import (
    MODEL_LABELS as SAVED_MODEL_LABELS,
    compute_model_progress,
    compute_preliminary_scores,
    compute_sample_clause_counts,
    get_ground_truth,
    list_contracts_for_picker,
    merge_saved_results,
)

LIVE_MODEL_LABELS = {
    "gemini_3_5_flash_lite": "Gemini 3.5 Flash-Lite (free)",
    "gemini_3_1_flash_lite": "Gemini 3.1 Flash-Lite (free)",
    "llama_local": "Llama 3.2 (local, free)",
    "claude_sonnet": "Claude Sonnet 5.5 (paid — costs real money per use)",
}


def extract_json(text):
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


def analyze_live(contract_text: str, model_key: str) -> dict:
    """Run every chunk through one model right now, merging results per clause type."""
    chunks = chunk_contract(contract_text)
    merged = {key: {"present": False, "quote": None} for key in CLAUSE_DEFINITIONS}
    errors = []

    progress = st.progress(0.0, text=f"Running {LIVE_MODEL_LABELS[model_key]}...")
    for i, chunk in enumerate(chunks, 1):
        prompt = build_prompt(chunk)
        result = CALLERS[model_key](prompt)
        if result["error"]:
            errors.append(result["error"])
        else:
            parsed = extract_json(result["text"])
            if parsed:
                for clause_key, info in parsed.items():
                    if clause_key in merged and info.get("present") and not merged[clause_key]["present"]:
                        merged[clause_key] = {"present": True, "quote": info.get("quote")}
        progress.progress(i / len(chunks), text=f"Running {LIVE_MODEL_LABELS[model_key]}... ({i}/{len(chunks)} sections)")
    progress.empty()
    return {"clauses": merged, "errors": errors}


def render_results(results: dict, model_labels: dict, ground_truth: dict | None = None) -> None:
    """results: {model_key: {"clauses": {...}, "errors": [...]}}"""
    models = list(results.keys())
    for clause_key, description in CLAUSE_DEFINITIONS.items():
        with st.expander(f"**{clause_key.replace('_', ' ').title()}** — {description}", expanded=True):
            n_cols = len(models) + (1 if ground_truth else 0)
            cols = st.columns(n_cols)
            col_i = 0

            if ground_truth:
                with cols[col_i]:
                    st.markdown("**Lawyer's real answer**")
                    truth = ground_truth[clause_key]
                    if truth["present"]:
                        st.info("Present")
                        st.caption(f"“{truth['quote']}”")
                    else:
                        st.info("Not present")
                col_i += 1

            for model in models:
                outcome = results[model]
                info = outcome["clauses"][clause_key]
                with cols[col_i]:
                    st.markdown(f"**{model_labels[model]}**")
                    if outcome.get("errors"):
                        st.warning("Unreliable — this model had errors")
                    elif info["present"]:
                        correct_marker = ""
                        if ground_truth and ground_truth[clause_key]["present"]:
                            correct_marker = " ✅"
                        elif ground_truth and not ground_truth[clause_key]["present"]:
                            correct_marker = " ❌ (false positive)"
                        st.success(f"Found{correct_marker}")
                        st.caption(f"“{info['quote']}”")
                    else:
                        missed_marker = ""
                        if ground_truth and ground_truth[clause_key]["present"]:
                            missed_marker = " ❌ (missed)"
                        st.error(f"Not found{missed_marker}")
                col_i += 1


st.set_page_config(page_title="Contract Clause Finder", layout="wide")
st.title("Contract Clause Finder")
st.caption(
    "A demo built on top of the AI Contract Review Evaluation project. "
    "Not legal advice."
)

summary_tab, browse_tab, paste_tab = st.tabs(
    ["Project summary", "Browse the 130 real results", "Paste a new contract"]
)

with summary_tab:
    st.subheader("Dataset")
    st.markdown(
        "**[CUAD](https://huggingface.co/datasets/theatticusproject/cuad)** "
        "(Contract Understanding Atticus Dataset) — 510 real commercial contracts, "
        "lawyer-labeled across 41 clause categories. This project uses a random, "
        "reproducible sample of **130** of them."
    )
    clause_counts = compute_sample_clause_counts()
    st.table({
        "Clause type": [k.replace("_", " ").title() for k in clause_counts],
        "Present in sample": [f"{v}/130 ({v/130:.0%})" for v in clause_counts.values()],
    })

    st.subheader("Models")
    st.markdown(
        "5 considered, 3 free models fully in the run, Claude pending a cost decision, "
        "Groq dropped (its free model's hidden reasoning tokens made it impractically slow, "
        "and the only non-reasoning free alternative was excluded on vendor-trust grounds)."
    )
    for model_key, label in SAVED_MODEL_LABELS.items():
        progress = compute_model_progress(model_key)
        st.progress(
            progress["complete"] / progress["total"],
            text=f"{label}: {progress['complete']}/{progress['total']} contracts complete",
        )

    st.subheader("Preliminary accuracy (not the final Stage 5 scoring)")
    st.caption(
        "Computed live from whatever results are saved so far — only counts contracts a "
        "model has actually completed. No confidence intervals here; that's Stage 5's job."
    )
    for model_key, label in SAVED_MODEL_LABELS.items():
        scores = compute_preliminary_scores(model_key)
        st.markdown(f"**{label}** — based on {scores['contracts_used']}/130 contracts so far")
        rows = {"Clause type": [], "Precision": [], "Recall": []}
        for clause_key, s in scores["clauses"].items():
            rows["Clause type"].append(clause_key.replace("_", " ").title())
            rows["Precision"].append(f"{s['precision']:.0%}" if s["precision"] is not None else "—")
            rows["Recall"].append(f"{s['recall']:.0%}" if s["recall"] is not None else "—")
        st.table(rows)

with browse_tab:
    contract_pairs = list_contracts_for_picker()
    labels = [label for _, label in contract_pairs]
    label_to_filename = {label: filename for filename, label in contract_pairs}
    chosen_label = st.selectbox("Pick a contract from the real 130-contract sample", labels)
    chosen = label_to_filename[chosen_label] if chosen_label else None
    st.caption(f"Actual file: {chosen}")

    available_models = list(SAVED_MODEL_LABELS.keys())
    selected_models = st.multiselect(
        "Which model(s) to show",
        options=available_models,
        default=available_models,
        format_func=lambda k: SAVED_MODEL_LABELS[k],
    )

    if chosen and selected_models:
        results = {model: merge_saved_results(model, chosen) for model in selected_models}
        ground_truth = get_ground_truth(chosen)

        incomplete = [m for m, r in results.items() if r["chunks_found"] == 0]
        if incomplete:
            st.warning(
                f"No saved results yet for: {', '.join(SAVED_MODEL_LABELS[m] for m in incomplete)} "
                "on this contract — that model's full run may still be in progress."
            )

        st.subheader("Results — compared against the lawyers' real labels")
        render_results(
            {m: {"clauses": r["clauses"], "errors": ["incomplete"] if r["had_error"] else []}
             for m, r in results.items()},
            SAVED_MODEL_LABELS,
            ground_truth=ground_truth,
        )

with paste_tab:
    contract_text = st.text_area(
        "Paste contract text here",
        height=250,
        placeholder="Paste the full text of a contract...",
    )

    uploaded = st.file_uploader("...or upload a file instead", type=["txt", "pdf"])
    if uploaded is not None:
        if uploaded.name.lower().endswith(".pdf"):
            reader = PdfReader(uploaded)
            contract_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            contract_text = uploaded.read().decode("utf-8", errors="replace")
        st.info(f"Loaded {uploaded.name} ({len(contract_text):,} characters)")

    if "live_model_select" not in st.session_state:
        st.session_state.live_model_select = ["gemini_3_5_flash_lite"]

    label_col, button_col = st.columns([4, 1])
    with label_col:
        st.write("Which model(s) to run")
    with button_col:
        if st.button("Select all", key="select_all_live"):
            st.session_state.live_model_select = list(LIVE_MODEL_LABELS.keys())

    selected_models = st.multiselect(
        "Which model(s) to run",
        options=list(LIVE_MODEL_LABELS.keys()),
        format_func=lambda k: LIVE_MODEL_LABELS[k],
        key="live_model_select",
        label_visibility="collapsed",
    )

    if "claude_sonnet" in selected_models:
        st.warning("Claude Sonnet 5.5 is a paid model — running it costs a small real amount per use.")

    if st.button("Analyze", type="primary", disabled=not contract_text or not selected_models):
        results = {model: analyze_live(contract_text, model) for model in selected_models}

        for model, outcome in results.items():
            if outcome["errors"]:
                st.error(
                    f"**{LIVE_MODEL_LABELS[model]} failed on {len(outcome['errors'])} section(s)** — "
                    f"results for this model below are incomplete, not a real \"not found\". "
                    f"First error: {outcome['errors'][0][:300]}"
                )

        st.subheader("Results")
        render_results(results, LIVE_MODEL_LABELS)
