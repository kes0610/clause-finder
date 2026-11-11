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

## Stage 4 — Full evaluation (complete — all 4 models)

**4 models run in total.** Dropped Groq's gpt-oss-120b partway through — its hidden
"reasoning" tokens burned through Groq's 200,000 tokens/day free cap so fast that
finishing all 130 contracts would have taken roughly a month at that rate. The only
other free, non-reasoning model Groq hosts is Alibaba's Qwen, which was excluded on
vendor-trust grounds — a business/data-governance call, not a technical one, and itself
a fair thing to note in the final memo (vendor trust is a real factor companies weigh,
not just accuracy/cost).

**Final results:**

| Model | Chunks done | Status |
|---|---|---|
| Llama 3.2 (local) | 527/527 (100%) | Complete |
| Gemini 3.5 Flash-Lite | 527/527 (100%) | Complete — took 2 resumed runs across 2 days to clear its daily free limit (confirmed: **500 requests/day**, undocumented) |
| Gemini 3.1 Flash-Lite | 527/527 (100%) | Complete — same, cleared over 2 days |
| Claude Sonnet 5.5 (paid) | 527/527 (100%) | Complete — one single run, 20.5 minutes, no daily quota limits to work around (paid tier) |
| ~~gpt-oss-120b (Groq)~~ | 44/527 (8%) | Dropped — see above. Partial output kept in `data/model_outputs/dropped_groq_attempt/` for the record, excluded from scoring |

All 130 contracts now have a complete, error-free result from all 4 models actually
scored. Next: Stage 5's rigorous scoring (confidence intervals, not just the point
estimates below).

**Preliminary precision/recall, Claude Sonnet 5.5 (all 130 contracts, unweighted point
estimates — not the final Stage 5 numbers):**

| Clause type | Precision | Recall |
|---|---|---|
| Termination | 72% | 93% |
| Liability Cap | 97% | 46% |
| Non-Compete | 77% | 79% |
| Renewal Term | 98% | 87% |
| Renewal Notice | 88% | 91% |
| Governing Law | 99% | 99% |
| Exclusivity | 84% | 84% |

Clearly stronger than the 3 free models across the board, with one notable exception:
Liability Cap recall is low (46%) despite near-perfect precision (97%) — Claude is
conservative here, only flagging a clause as a liability cap when very confident, and
missing over half of the real ones as a result. Worth digging into in Stage 5 (is this a
prompt-wording issue, or a genuine model weakness on this clause type specifically).

Note: ad-hoc test/debug calls to the same API key count against the same daily
limit as the real run — worth remembering before poking at a model mid-run.

Two real bugs caught and fixed mid-run: a Gemini request that hung indefinitely with no
timeout (stalled that whole model's progress silently for over an hour), and a
rate-limit message that looked like a long daily block but actually cleared in ~2
minutes — the retry logic now reads the server's own suggested wait time instead of
guessing.

## Stage 5 — Scoring (complete)

Real precision, recall, and F1 for all 4 models across all 7 clause types, computed
over all 130 contracts — plus a 95% confidence interval for precision and recall,
built by bootstrap resampling (resample the 130 contracts with replacement 10,000
times, recompute the score each time, take the middle 95% of those 10,000 results).
This answers a question the Stage 4 "preliminary" numbers couldn't: how much would
these scores wobble on a different sample of 130 real contracts? A narrow interval
(e.g. Governing Law, ~97-100%) means the number is solid; a wide one (e.g. Llama's
Non-Compete, 32-76% precision) means there isn't enough data yet to trust the point
estimate on its own. Script: `scripts/05_scoring.py`. Full numbers (including raw
true/false positive/negative counts): `data/model_outputs/stage5_scoring.json`.

**Gemini 3.5 Flash-Lite**

| Clause type | Precision | 95% CI | Recall | 95% CI | F1 |
|---|---|---|---|---|---|
| Termination | 42% | 33-51% | 100% | 100-100% | 59% |
| Liability Cap | 96% | 90-100% | 71% | 60-81% | 82% |
| Non-Compete | 74% | 57-90% | 69% | 52-85% | 71% |
| Renewal Term | 92% | 85-98% | 94% | 87-100% | 93% |
| Renewal Notice | 78% | 64-91% | 91% | 79-100% | 84% |
| Governing Law | 99% | 97-100% | 100% | 100-100% | 100% |
| Exclusivity | 67% | 54-79% | 88% | 78-97% | 76% |

**Gemini 3.1 Flash-Lite**

| Clause type | Precision | 95% CI | Recall | 95% CI | F1 |
|---|---|---|---|---|---|
| Termination | 47% | 37-58% | 98% | 92-100% | 64% |
| Liability Cap | 89% | 80-98% | 61% | 49-72% | 72% |
| Non-Compete | 70% | 53-85% | 79% | 63-93% | 74% |
| Renewal Term | 96% | 90-100% | 90% | 82-98% | 93% |
| Renewal Notice | 86% | 74-97% | 97% | 89-100% | 91% |
| Governing Law | 99% | 97-100% | 100% | 100-100% | 100% |
| Exclusivity | 70% | 58-82% | 93% | 85-100% | 80% |

**Llama 3.2 (local)**

| Clause type | Precision | 95% CI | Recall | 95% CI | F1 |
|---|---|---|---|---|---|
| Termination | 43% | 32-54% | 82% | 70-93% | 56% |
| Liability Cap | 83% | 70-94% | 49% | 38-61% | 62% |
| Non-Compete | 55% | 32-76% | 38% | 21-56% | 45% |
| Renewal Term | 60% | 46-73% | 63% | 50-76% | 62% |
| Renewal Notice | 57% | 38-75% | 50% | 32-68% | 53% |
| Governing Law | 99% | 97-100% | 80% | 73-88% | 89% |
| Exclusivity | 61% | 48-74% | 77% | 63-89% | 68% |

**Claude Sonnet 5.5 (paid)**

| Clause type | Precision | 95% CI | Recall | 95% CI | F1 |
|---|---|---|---|---|---|
| Termination | 72% | 60-83% | 93% | 85-100% | 81% |
| Liability Cap | 97% | 90-100% | 46% | 35-58% | 63% |
| Non-Compete | 77% | 61-91% | 79% | 63-93% | 78% |
| Renewal Term | 98% | 93-100% | 87% | 76-95% | 92% |
| Renewal Notice | 88% | 76-97% | 91% | 79-100% | 89% |
| Governing Law | 99% | 97-100% | 99% | 97-100% | 99% |
| Exclusivity | 84% | 72-94% | 84% | 72-94% | 84% |

**Failure patterns, confirmed across the full 130-contract dataset:**

- **Termination: every model over-flags it**, precision stuck at 42-47% for the 3
  free models (recall near-perfect, 82-100%) — they treat almost any mention of
  ending the contract as "termination for convenience," including ordinary
  for-cause termination clauses. Claude does noticeably better here (72% precision)
  but still over-flags relative to its other clause types.
- **Liability Cap: every single model has weak recall** (46-71%) despite strong
  precision (83-97%) — all 4 models are conservative here, missing roughly a
  third to half of the real liability caps rather than risking a false flag. This
  is the clearest cross-model pattern in the whole dataset and likely reflects
  how liability caps are phrased in these contracts (often buried in dense
  indemnification language) rather than any one model's weakness.
- **Llama is meaningfully weaker than both Gemini models and Claude** on
  Non-Compete, Renewal Term, and Renewal Notice specifically — its confidence
  intervals are also the widest of the 4 models on these (e.g. Non-Compete
  precision 32-76%), meaning there's real uncertainty in its score, not just a
  lower point estimate.
- Governing Law is solved by every model (99-100% precision, 80-100% recall) —
  it's a highly standardized, easy-to-spot clause type in commercial contracts.

## Stage 6 — Human-review line (complete)

**Decision rule** (based on Stage 5's numbers for Claude Sonnet 5.5, the strongest
model overall — a company accepting lower accuracy for a free model should move the
line further toward "always review," see note below):

- **Trust the AI alone** — precision and recall both ≥95%
- **AI drafts, human spot-checks a sample** — precision and recall both ≥75%, but not
  both ≥95%
- **Always needs human review** — precision or recall below 75% for either reason
  (over-flagging too many false positives, or under-flagging too many real clauses)

**Applied to Claude Sonnet 5.5's results:**

| Clause type | Precision | Recall | Line |
|---|---|---|---|
| Governing Law | 99% | 99% | Trust AI alone |
| Renewal Term | 98% | 87% | AI drafts, human spot-checks |
| Renewal Notice | 88% | 91% | AI drafts, human spot-checks |
| Non-Compete | 77% | 79% | AI drafts, human spot-checks |
| Exclusivity | 84% | 84% | AI drafts, human spot-checks |
| Termination | 72% | 93% | **Always review** — precision below 75%, over-flags for-cause terminations as "for convenience" |
| Liability Cap | 97% | 46% | **Always review** — recall below 75%, misses roughly half the real caps |

**If a company uses a free model instead of Claude** (to avoid the ~$7-11/130-contract
cost), the line moves significantly. Using Gemini 3.5 Flash-Lite (the strongest free
model) as the reference: Non-Compete (74%/69%) and Exclusivity (67%/88%) would also
drop into "always review." Using Llama 3.2 instead: Non-Compete, Renewal Term, and
Renewal Notice all fall below the 75% line on one or both metrics, meaning only
Governing Law and Liability Cap's precision (not its recall) would be left as
AI-draftable without constant human review — i.e. the cheaper the model, the more of
the contract still needs a human, which is the real cost/accuracy tradeoff a company
is making, not just the API price.

## Stage 7 — Recommendation (not started)

## Stage 7 — Recommendation (not started)
