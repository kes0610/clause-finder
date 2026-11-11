# AI-Assisted Contract Clause Review — Evaluation & Recommendation

**To:** Legal Operations / General Counsel
**Re:** Whether to use AI to speed up first-pass review of commercial contracts, and which model

**Not legal advice.** This evaluates AI models as a research/drafting aid for human
reviewers, not as a substitute for legal judgment.

## Summary

We tested 4 AI models (3 free, 1 paid) on 130 real commercial contracts, checking
whether each model could correctly identify 7 common clause types against a
lawyer-labeled answer key. **Claude Sonnet 5.5 (paid, ~$7-11 total for this sample —
roughly $0.05-0.08 per contract) is the clearest overall choice**, with meaningfully
better precision than any free option, especially on clauses where free models
generate a lot of false alarms. That said, **no model is accurate enough to leave
unsupervised on every clause type** — two of the seven need a human reviewer
regardless of which model is used.

## What we tested

130 contracts, randomly sampled from CUAD (Contract Understanding Atticus Dataset —
510 real commercial contracts with lawyer-applied labels across 41 clause categories,
CC BY 4.0, Hendrycks et al. 2021). We scoped this to 7 clause types most relevant to a
routine contract-review workflow: Termination, Liability Cap, Non-Compete, Renewal
Term, Renewal Notice, Governing Law, and Exclusivity. Every model was given the same
prompt and the same contract text, split into the same token-sized chunks, so the
comparison is apples-to-apples. Full methodology and every number behind this memo:
`RESULTS.md` in this repository.

## Results by clause type (Claude Sonnet 5.5, the recommended model)

| Clause type | Precision | Recall | Human review needed? |
|---|---|---|---|
| Governing Law | 99% | 99% | No — trust the AI |
| Renewal Term | 98% | 87% | Spot-check a sample |
| Renewal Notice | 88% | 91% | Spot-check a sample |
| Exclusivity | 84% | 84% | Spot-check a sample |
| Non-Compete | 77% | 79% | Spot-check a sample |
| **Termination** | **72%** | 93% | **Yes, always** — flags many ordinary for-cause terminations as "termination for convenience" |
| **Liability Cap** | 97% | **46%** | **Yes, always** — misses roughly half of the real liability caps |

(Precision = of the clauses the AI flagged, how many were real. Recall = of the real
clauses, how many the AI found. The "human review needed" line is a threshold we set
at under 75% on either metric — see `RESULTS.md` Stage 6 for the full rule and numbers
for all 4 models.)

## Why Claude over a free model

The free models (Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite, and a locally-run Llama
3.2) cost nothing per use but are meaningfully less accurate, and the gap isn't evenly
spread — it concentrates in exactly the clauses that matter most. On Termination, for
example, every free model's precision sits at 42-47% (vs. Claude's 72%), meaning a
reviewer using a free model would spend much more time chasing false alarms. Using the
cheapest model (local Llama) pushes three additional clause types below the "needs
human review" line — Non-Compete, Renewal Term, and Renewal Notice — on top of the two
that need review no matter what. At the contract volumes a mid-size legal team
realistically handles, the per-contract cost difference (a few cents) is small
relative to the reviewer time saved by not chasing false positives.

## Estimated impact — assumptions, not measured results

We did not measure actual review-time savings; the following is a labeled estimate for
planning purposes only, built on an assumption a legal ops team should sanity-check
against its own numbers:

- **Assumption:** a reviewer currently spends roughly 10-15 minutes per contract
  manually locating these 7 clauses.
- **If so:** the 5 clause types in the "spot-check" tier plus Governing Law (6 of 7)
  could have a first-pass answer pre-filled by the AI, with the reviewer confirming
  rather than searching from scratch — plausibly cutting review time for those clauses
  by half or more.
- Termination and Liability Cap would still need full manual review, so total
  time savings per contract would be well under the "6 of 7 clauses" figure above —
  realistically in the range of a modest, not dramatic, reduction until those two
  clause types are investigated further (see Limitations).

## Limitations

- **Sample and source:** 130 contracts from CUAD, which is itself a sample of older,
  mostly SEC-filed U.S. commercial contracts. Results may not generalize to contract
  types CUAD doesn't cover (e.g. employment agreements, NDAs) or to non-U.S. contracts.
- **Ground truth itself:** the "real answers" are CUAD's own lawyer labels, which are
  high-quality but not infallible — some of what we're scoring as a model's error could
  be a labeling disagreement rather than a model mistake.
- **One-time snapshot:** model versions and pricing change; these exact numbers will
  drift over time and should be re-checked periodically, not treated as permanent.
- **Liability Cap's low recall is unexplained.** It's consistent across all 4 models,
  which suggests it's about how these contracts phrase liability caps (often buried in
  dense indemnification language) rather than a weakness specific to one model — worth
  a follow-up look at the actual missed examples before assuming the pattern is fixed.
- This was evaluated as a drafting aid for a human reviewer, not tested or validated
  as a legal-advice tool, and should never be deployed as one.
