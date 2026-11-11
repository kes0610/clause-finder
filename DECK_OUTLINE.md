# Slide Deck Outline — AI-Assisted Contract Clause Review

Outline only (not built slide-by-slide) — each bullet below is one slide's worth of
content. Pulls directly from `MEMO.md` and `RESULTS.md`; no numbers here that aren't
in those two files.

**1. Title**
AI-Assisted Contract Clause Review: Evaluation & Recommendation

**2. The question**
Can an AI model reliably spot key clauses in a contract, well enough to speed up
review — and if so, which model? Framed as a drafting aid for a human reviewer, not a
legal-advice tool.

**3. Method**
- 130 real commercial contracts, randomly sampled from CUAD (lawyer-labeled, CC BY 4.0)
- 7 clause types: Termination, Liability Cap, Non-Compete, Renewal Term, Renewal
  Notice, Governing Law, Exclusivity
- 4 models tested, same prompt/chunking for all — 3 free (2 Gemini tiers, local Llama
  3.2), 1 paid (Claude Sonnet 5.5)
- Scored against the lawyers' real answers: precision, recall, 95% confidence
  intervals (bootstrap over the 130 contracts)

**4. Headline result**
Claude Sonnet 5.5 is the strongest model overall — table: best/worst clause type per
model, pulled from `RESULTS.md` Stage 5.

**5. The one universal weak spot**
Liability Cap recall is weak on every model (46-71%) despite strong precision — all 4
models are conservative, missing a third to half of real liability caps. Flag as the
single most important finding to act on, not model-specific.

**6. The human-review line**
3-tier chart: "Trust AI alone" (Governing Law only) / "AI drafts, human spot-checks"
(4 clause types) / "Always needs a human" (Termination, Liability Cap) — and how this
line gets stricter the cheaper the model (full table in `RESULTS.md` Stage 6).

**7. Cost vs. accuracy**
Free models cost $0 but push 3 more clause types into "always needs a human."
Claude costs ~$0.05-0.08/contract. At realistic contract volumes, the cost gap is
small relative to reviewer time saved by fewer false alarms.

**8. Recommendation**
Use Claude Sonnet 5.5 as the primary model. Keep mandatory human review on Termination
and Liability Cap no matter which model is used.

**9. Estimated impact (label clearly as an assumption, not a measured result)**
If a reviewer spends ~10-15 min/contract today, pre-filling 6 of 7 clause types could
meaningfully cut that — but Termination and Liability Cap still need full manual
review, so total savings are moderate, not dramatic, until those two are improved.

**10. Limitations**
Dataset is older/U.S.-centric SEC filings; ground truth is CUAD's own labels, not
infallible; one-time snapshot — model versions and pricing will change; Liability
Cap's cause is still unexplained and worth a follow-up look.
