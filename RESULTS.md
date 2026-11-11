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
| Gemini 3.5 Flash-Lite | Google AI Studio | Yes | Swapped in for 3.8 Flash during Stage 3 — see below |
| Gemini 3.1 Flash-Lite | Google AI Studio | Yes | Google's most basic free-tier model |
| ~~openai/gpt-oss-120b~~ | Groq (free plan) | Yes | Dropped during Stage 4 — see below |
| Llama 3.2 (3B) | Local, via Ollama | Yes | Runs on-device, no API key, no rate limit — pulled and verified working |
| Claude Sonnet 5.5 | Anthropic | **No — paid** | See Stage 3 for a revised, measured cost estimate |

API keys for Google, Groq, and Anthropic are stored in `.env` (not committed — see `.env.example`).

## Stage 3 — Pilot run (done)

**Prompt and chunking:** one shared prompt ([lib/clause_extraction.py](lib/clause_extraction.py))
asks for all 7 clause types per request, structured JSON output. Contracts are split into
~3000-token pieces with 200-token overlap (median contract: ~7,060 tokens; longest: 62,009 —
far past what a single request should carry), using the same splitting rule for every model so
the comparison stays fair.

**Pilot:** ran the first 5 sampled contracts (22 chunks total) through all 5 models — 110
requests. Caught and fixed 3 real bugs before they could waste a full run:
- **Gemini 3.8 Flash's free tier allows only 20 requests/day** (not published anywhere, only
  discovered by hitting it) — swapped for Gemini 3.5 Flash-Lite, which has no such limit.
- Local Llama's context window (Ollama's default) was too small, silently truncating answers
  mid-JSON — fixed by raising it.
- Claude Sonnet 5.5 sometimes returns an internal "thinking" block before its actual answer,
  which crashed our original parsing code — fixed to find the real text block.

**After fixes, re-running the same pilot:**

| Model | Parsed OK | Errors | Avg seconds/request |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | 22/22 | 0 | 1.6 |
| Gemini 3.1 Flash-Lite | 22/22 | 0 | 0.8 |
| gpt-oss-120b (Groq) | 22/22 | 0 | 17.1 |
| Llama 3.2 (local) | 21/22 | 0 | 14.6 |
| Claude Sonnet 5.5 | 22/22 | 0 | 2.6 |

(The 1 Llama parse failure was the model itself forgetting a closing `}` — a known small-model
weakness, not a bug in our code; a lenient repair step now catches this specific pattern.)

**Interesting finding:** Groq's gpt-oss-120b is a "reasoning" model that generates a lot of
hidden internal reasoning tokens before its visible answer — that's the real reason it's slower
and uses far more tokens than the other models for the same question, even though its visible
JSON answer is just as compact.

**Projected for the full 130-contract run** (scaled up from the pilot's real, measured numbers):

| Model | Est. requests | Est. time | Est. cost |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | ~527 | ~14 min | Free |
| Gemini 3.1 Flash-Lite | ~527 | ~7 min | Free |
| gpt-oss-120b (Groq) | ~527 | ~2.5 hours | Free (within Groq's 1,000/day cap) |
| Llama 3.2 (local) | ~527 | ~2.1 hours | Free (runs on this laptop) |
| Claude Sonnet 5.5 | ~527 | ~22 min | **~$7-11 (revised estimate — see note)** |

**Cost estimate revision:** the Stage 2 estimate of "$1-2" for Claude didn't account for
chunking — splitting each contract into several pieces multiplies the number of requests, and
the clause instructions get resent with every chunk. The pilot's real, measured token counts put
the full run closer to **$7-11**, not $1-2. Flagging this clearly since it changes the actual
cost of the one paid model in the comparison.

Two Google free-tier daily limits are still unconfirmed (Gemini doesn't publish them) — the
pilot didn't hit either one, but Stage 4's full run needs to handle hitting one gracefully
(save progress, pause, resume) rather than assume 527 requests/day is guaranteed available.

## Stage 4 — Full evaluation (complete for the 3 free models)

**Models actually run: 3 free + Claude still pending a decision.** Dropped Groq's
gpt-oss-120b partway through — its hidden "reasoning" tokens burned through Groq's
200,000 tokens/day free cap so fast that finishing all 130 contracts would have taken
roughly a month at that rate. The only other free, non-reasoning model Groq hosts is
Alibaba's Qwen, which was excluded on vendor-trust grounds — a business/data-governance
call, not a technical one, and itself a fair thing to note in the final memo (vendor
trust is a real factor companies weigh, not just accuracy/cost).

**Final results:**

| Model | Chunks done | Status |
|---|---|---|
| Llama 3.2 (local) | 527/527 (100%) | Complete |
| Gemini 3.5 Flash-Lite | 527/527 (100%) | Complete — took 2 resumed runs across 2 days to clear its daily free limit (confirmed: **500 requests/day**, undocumented) |
| Gemini 3.1 Flash-Lite | 527/527 (100%) | Complete — same, cleared over 2 days |
| ~~gpt-oss-120b (Groq)~~ | 44/527 (8%) | Dropped — see above. Partial output kept in `data/model_outputs/dropped_groq_attempt/` for the record, excluded from scoring |

All 130 contracts now have a complete, error-free result from all 3 free models.
Next: decide on running Claude Sonnet 5.5 (~$7-11), then Stage 5's real scoring.

Note: ad-hoc test/debug calls to the same API key count against the same daily
limit as the real run — worth remembering before poking at a model mid-run.

Two real bugs caught and fixed mid-run: a Gemini request that hung indefinitely with no
timeout (stalled that whole model's progress silently for over an hour), and a
rate-limit message that looked like a long daily block but actually cleared in ~2
minutes — the retry logic now reads the server's own suggested wait time instead of
guessing.

## Stage 5 — Scoring (not started)

## Stage 6 — Human-review line (not started)

## Stage 7 — Recommendation (not started)
