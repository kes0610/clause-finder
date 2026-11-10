"""
Bonus interactive tool (not part of the original 7-stage assignment) —
paste in a contract, pick which AI model(s) to try, and see what each one
finds for the same 7 clause types used in the full evaluation.

Reuses the exact same prompt/chunking/model-calling code as the real
evaluation (lib/), so this isn't a separate, unvalidated code path — it's
the same logic the scored results came from.

Run with: streamlit run tool/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from lib.clause_extraction import CLAUSE_DEFINITIONS, build_prompt, chunk_contract
from lib.model_clients import CALLERS

MODEL_LABELS = {
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
    import json
    for extra_braces in ("", "}", "}}", "}}}"):
        try:
            return json.loads(cleaned + extra_braces)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def analyze(contract_text: str, model_key: str) -> dict:
    """Run every chunk through one model, merging results per clause type.

    Returns {"clauses": {...}, "errors": [...]} — errors is non-empty if any
    chunk's call failed (e.g. hit a free-tier daily limit), so the caller
    can show that honestly instead of silently rendering "not found".
    """
    chunks = chunk_contract(contract_text)
    merged = {key: {"present": False, "quote": None} for key in CLAUSE_DEFINITIONS}
    errors = []

    progress = st.progress(0.0, text=f"Running {MODEL_LABELS[model_key]}...")
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
        progress.progress(i / len(chunks), text=f"Running {MODEL_LABELS[model_key]}... ({i}/{len(chunks)} sections)")
    progress.empty()
    return {"clauses": merged, "errors": errors}


st.set_page_config(page_title="Contract Clause Finder", layout="wide")
st.title("Contract Clause Finder")
st.caption(
    "A demo built on top of the AI Contract Review Evaluation project. "
    "Paste in a contract and see what each AI model finds — not legal advice."
)

contract_text = st.text_area(
    "Paste contract text here",
    height=250,
    placeholder="Paste the full text of a contract...",
)

uploaded = st.file_uploader("...or upload a .txt file instead", type=["txt"])
if uploaded is not None:
    contract_text = uploaded.read().decode("utf-8", errors="replace")
    st.info(f"Loaded {uploaded.name} ({len(contract_text):,} characters)")

selected_models = st.multiselect(
    "Which model(s) to run",
    options=list(MODEL_LABELS.keys()),
    default=["gemini_3_5_flash_lite"],
    format_func=lambda k: MODEL_LABELS[k],
)

if "claude_sonnet" in selected_models:
    st.warning("Claude Sonnet 5.5 is a paid model — running it costs a small real amount per use.")

if st.button("Analyze", type="primary", disabled=not contract_text or not selected_models):
    results = {model: analyze(contract_text, model) for model in selected_models}

    for model, outcome in results.items():
        if outcome["errors"]:
            st.error(
                f"**{MODEL_LABELS[model]} failed on {len(outcome['errors'])} section(s)** — "
                f"results for this model below are incomplete, not a real \"not found\". "
                f"First error: {outcome['errors'][0][:300]}"
            )

    st.subheader("Results")
    for clause_key, description in CLAUSE_DEFINITIONS.items():
        with st.expander(f"**{clause_key.replace('_', ' ').title()}** — {description}", expanded=True):
            cols = st.columns(len(selected_models))
            for col, model in zip(cols, selected_models):
                info = results[model]["clauses"][clause_key]
                with col:
                    st.markdown(f"**{MODEL_LABELS[model]}**")
                    if results[model]["errors"]:
                        st.warning("Unreliable — this model had errors")
                    elif info["present"]:
                        st.success("Found")
                        st.caption(f"“{info['quote']}”")
                    else:
                        st.error("Not found")
