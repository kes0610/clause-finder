# Glossary

Plain-English definitions for every technical term used in this project,
added the first time each one shows up. If you hit a term anywhere in this
repo that isn't here yet, that's a bug — ask and it'll get added.

**LLM (Large Language Model)** — an AI model trained on huge amounts of text
that can read and write natural language. ChatGPT and Gemini are built on
LLMs. Example: you give an LLM a contract and ask "does this have a
non-compete clause?" and it answers in plain English.

**Model** — one specific version of an AI system (e.g. "Gemini 2.0 Flash").
Different models can give different answers to the same question, which is
exactly what this project is comparing.

**Dataset** — a collection of examples used for research or testing. Example:
CUAD is a dataset of 510 real contracts.

**Label** — the correct answer attached to one example in a dataset, usually
written by a human expert. Example: a lawyer labeling "this contract HAS a
non-compete clause, and here's the exact sentence."

**Ground truth** — the labels we treat as "known correct" when scoring a
model, because a human expert produced them. Example: CUAD's lawyer labels
are our ground truth — we check the AI's answers against them, not the
other way around.

**Clause** — a specific section or sentence in a contract that covers one
topic, like how/when it can be ended (a "termination clause") or who can't
compete with whom (a "non-compete clause").

**CSV (Comma-Separated Values)** — a plain-text spreadsheet format, where
each line is a row and commas separate the columns. Example: Excel can open
a CSV, and so can a few lines of Python code.

**License (e.g. CC BY 4.0)** — the legal terms under which you're allowed to
use someone else's work. "CC BY 4.0" (Creative Commons Attribution 4.0)
means: you can use, share, and build on this freely, as long as you credit
the original creators. That's why this project cites the CUAD paper.

**Virtual environment** — an isolated, self-contained set of Python
packages for one project, so installing something for this project can't
break or conflict with another project's setup. Example: this project's
`.venv` folder is separate from any Python packages installed elsewhere on
this computer.

**Random seed** — a starting number that makes a "random" choice
reproducible. Example: "pick 130 random contracts with seed 42" will always
pick the *exact same* 130 contracts if you run it again — without a fixed
seed, you'd get a different 130 every time, and nobody (including future
you) could double-check the work.

**Sample** — a smaller subset chosen from a larger dataset, used instead of
the whole thing to save time/cost. Example: our 130-contract sample out of
CUAD's full 510.

**API (Application Programming Interface)** — a way for one piece of
software to ask another piece of software to do something, over the
internet. Example: instead of opening Gemini's website by hand, our code
sends the contract text to Google's API and gets Gemini's answer back
automatically.

**API key** — a private password-like string that proves to an API who's
asking, and lets the provider track/limit usage. Must never be put directly
in code or committed to GitHub — this project keeps keys in environment
variables (settings stored outside the code, in the computer's shell) or
Kaggle Secrets instead.

**Token** — a small chunk of text, roughly ¾ of a word, that's how LLMs
measure and charge for the text you send them. Example: "The cat sat" is
about 3-4 tokens. A free tier's limits and a paid API's price are both
usually expressed per token.

**Rate limit** — a cap on how many requests (or tokens) you can send an API
in a given time window, before it stops responding. Free tiers almost
always have tighter rate limits than paid ones.

**Precision** — of all the times the AI *said* a clause was present, what
fraction were actually correct? Example: if the AI flags 10 contracts as
having a non-compete clause but only 7 really do, precision is 7/10 = 70%.

**Recall** — of all the contracts that *actually* have a clause, what
fraction did the AI find? Example: if 20 contracts really have a non-compete
clause and the AI found 14 of them, recall is 14/20 = 70%.

**F1 score** — a single number that combines precision and recall into one
score (their "harmonic mean"), so you don't have to look at two numbers to
judge a model. Useful for ranking models when one has higher precision and
another has higher recall.

**False positive** — the AI says a clause is there, but it isn't. (Hurts
precision.)

**False negative** — the AI misses a clause that's actually there. (Hurts
recall.)

**Hallucination** — when an AI confidently states something that isn't true
or isn't actually in the source text. Example: the AI "quotes" a
non-compete clause that doesn't exist anywhere in the contract.

**Benchmark** — a standard test used to compare different models or systems
against each other on the same task.

**Confidence interval / margin of error** — a range around a measured
number that reflects how much it might shift if you repeated the test with
a different sample. Example: "72% recall, ± 8%" means the true value is
probably somewhere between 64% and 80% — useful so we don't claim one model
is "better" when the difference could just be random luck from a small
sample.

**Context window** — the maximum amount of text (measured in tokens) a
model can "see" at once, including both what you send it and what it
writes back. Example: if a model's context window is 8,000 tokens and your
contract is 60,000 tokens, it physically cannot read the whole thing in one
go — you have to split it up.

**Chunking** — splitting a long document into smaller pieces so each piece
fits inside a model's context window, usually with a little overlap between
pieces so something important doesn't get cut exactly in half.

**Reasoning model** — a type of AI model that generates hidden "thinking"
text to itself before writing its final visible answer, which usually makes
it slower and more expensive (since that hidden thinking still counts as
tokens used) but sometimes more accurate on hard questions.
