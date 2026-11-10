# AI Contract Review Evaluation

A portfolio project evaluating how well free AI models (large language models,
or "LLMs" — see [GLOSSARY.md](GLOSSARY.md)) can flag important clauses in
real commercial contracts, compared against lawyer-labeled ground truth.
Acting as a consultant, this project scores several free models on the same
contracts and recommends which a hypothetical mid-size company should use,
and which clause types still need a human reviewer.

**This is not legal advice.** The author is not a lawyer, and nothing here
should be used to make real legal decisions.

Status: Stage 3 (prompt + pilot run) complete. See [RESULTS.md](RESULTS.md)
for real numbers as they're produced — nothing in this README or that file
is invented or filled in ahead of an actual run.

## Setup

This project uses Python 3.9+ in its own virtual environment so it never
touches your system Python packages.

```bash
cd contract-review-eval
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**API keys:** copy `.env.example` to `.env` and fill in your own free keys
(Google AI Studio, Groq) plus an Anthropic key if you want to include the
one paid model. `.env` is git-ignored — never commit real keys.

## Models (Stage 2)

5 models, 4 free + 1 paid (clearly labeled):

| Model | Provider | Free? |
|---|---|---|
| Gemini 3.8 Flash | Google AI Studio | Yes |
| Gemini 3.1 Flash-Lite | Google AI Studio | Yes |
| openai/gpt-oss-120b | Groq (free plan) | Yes |
| Llama 3.2 (3B) | Local, via Ollama | Yes |
| Claude Sonnet 5.5 | Anthropic | **No — paid, ~$1-2 estimated** |

Mistral was considered but dropped — its advertised "free" plan actually
required upgrading (likely with a credit card) before the API key would
work, so it didn't meet the free-only bar.

## Data

This project uses [CUAD (Contract Understanding Atticus Dataset)](https://huggingface.co/datasets/theatticusproject/cuad):
510 real commercial contracts, hand-labeled by lawyers across 41 clause
categories (~13,000 labels total). It's licensed under **CC BY 4.0** (free
to use and redistribute, with attribution).

**Citation:**
> Hendrycks, D., Burns, C., Chen, A., & Ball, S. (2021). CUAD: An
> Expert-Annotated NLP Dataset for Legal Contract Review.
> [arXiv:2103.06268](https://arxiv.org/abs/2103.06268)

The raw dataset is **not committed to this repo** (per CUAD's own
distribution practice and to keep the repo small). To download it yourself:

```bash
mkdir -p data/raw
curl -sL "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/CUAD_v1/master_clauses.csv" \
  -o data/raw/master_clauses.csv
```

## Method so far

**Clause types chosen (Stage 1):** 6 clause types a business would care
about, mapped to CUAD's exact category names, picked for being common
enough in the data to score reliably:

| Plain-English name | CUAD category | Present in full dataset |
|---|---|---|
| Termination | Termination For Convenience | 183/510 (36%) |
| Liability cap | Cap On Liability | 275/510 (54%) |
| Non-compete | Non-Compete | 119/510 (23%) |
| Auto-renewal (term) | Renewal Term | 176/510 (35%) |
| Auto-renewal (notice to cancel) | Notice Period To Terminate Renewal | 111/510 (22%) |
| Governing law | Governing Law | 437/510 (86%) |
| Exclusivity | Exclusivity | 180/510 (35%) |

("Auto-renewal" is split into two CUAD categories — there's no single
combined one.)

**Contract sample:** A random sample of 130 contracts out of the full 510,
drawn with a fixed random seed (`42`) so it's exactly reproducible — see
[scripts/01_sample_contracts.py](scripts/01_sample_contracts.py). All 7
clause columns appear at least 29 times in the sample, which is enough to
compute reasonably stable accuracy scores later. The chosen contract
filenames are saved in `data/processed/sample_contracts.csv`.

## Reproducing Stage 1

```bash
source .venv/bin/activate
python scripts/01_sample_contracts.py
```

## Limitations (so far)

- CUAD covers specific commercial contract types used in corporate
  transactions (supply, licensing, distribution, etc.) — results won't
  necessarily generalize to other contract styles (e.g. consumer leases).
- Clause type counts above are for the full 510-contract dataset; later
  stages use the 130-contract sample, so exact counts differ slightly (see
  the script's own printed output).

## Bonus: interactive demo tool

Not part of the original assignment, but a nice extra for showing this off — a small
web page where you paste in a contract and see what each AI model finds, live.

```bash
source .venv/bin/activate
streamlit run tool/app.py
```

It reuses the exact same prompt/chunking/model code as the real evaluation
(`lib/`), so it's not a separate, unvalidated path — it's the same logic the
scored results come from.

## License

This project's own code is free to reuse. CUAD itself is CC BY 4.0 —
see the citation above.
