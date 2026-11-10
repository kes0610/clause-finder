# Results

Real numbers only — nothing here is invented or estimated ahead of an
actual run. Updated as each stage completes.

## Stage 1 — Scope (done)

- Dataset: CUAD, 510 contracts, 41 lawyer-labeled clause categories.
- Clause types chosen: 7 columns covering 6 plain-English clause types
  (termination, liability cap, non-compete, auto-renewal [2 columns],
  governing law, exclusivity).
- Sample: 130 contracts, random seed 42, drawn from the full 510.
- Clause type counts in the 130-contract sample:

  | Clause type | Count in sample | % of sample |
  |---|---|---|
  | Termination | 44/130 | 33.8% |
  | Liability cap | 69/130 | 53.1% |
  | Non-compete | 29/130 | 22.3% |
  | Renewal term | 52/130 | 40.0% |
  | Renewal notice | 32/130 | 24.6% |
  | Governing law | 112/130 | 86.2% |
  | Exclusivity | 43/130 | 33.1% |

## Stage 2 — Models (done — keys set up, local model pulled)

5 models, 4 free + 1 paid (clearly labeled as the one exception). Mistral was
considered but dropped: its free "Experiment" plan turned out to require
upgrading (and likely a credit card) to actually use the API, despite being
advertised as free — so it failed the "genuinely free" bar and was swapped
for Groq, which was independently confirmed free with no card.

| Model | Provider | Free? | Notes |
|---|---|---|---|
| Gemini 3.8 Flash | Google AI Studio | Yes | Google's current best free-tier model |
| Gemini 3.1 Flash-Lite | Google AI Studio | Yes | Google's most basic free-tier model |
| openai/gpt-oss-120b | Groq (free plan) | Yes | OpenAI's open-weight model, hosted free by Groq |
| Llama 3.2 (3B) | Local, via Ollama | Yes | Runs on-device, no API key, no rate limit — pulled and verified working |
| Claude Sonnet 5.5 | Anthropic | **No — paid** | ~$1-2 estimated for the full run; author's own existing key |

API keys for Google, Groq, and Anthropic are stored in `.env` (not committed — see `.env.example`).

Dates each model is actually run will be recorded here once Stage 3/4 happen, since free-tier
models and prices can change.

## Stage 3 — Pilot run (not started)

## Stage 4 — Full evaluation (not started)

## Stage 5 — Scoring (not started)

## Stage 6 — Human-review line (not started)

## Stage 7 — Recommendation (not started)
