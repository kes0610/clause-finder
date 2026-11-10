"""
The one shared prompt + chunking logic every model uses, so the comparison
across models is fair (same questions, same contract text, same splitting
rule for every one of them).
"""
import tiktoken

# Our 7 clause columns, in the same order every time, with a plain-English
# description so a model (and a human reading the prompt) knows exactly
# what counts.
CLAUSE_DEFINITIONS = {
    "termination": "A clause letting either party end the contract early, "
                   "without needing a specific reason (sometimes called "
                   "'termination for convenience').",
    "liability_cap": "A clause that limits the total dollar amount one party "
                      "could ever have to pay the other if something goes wrong.",
    "non_compete": "A clause stopping one party from operating a competing "
                    "business, during the contract or for some time after.",
    "renewal_term": "A clause describing whether and how the contract "
                     "automatically renews after its initial term ends.",
    "renewal_notice": "A clause stating how much advance notice is required "
                       "to stop the contract from automatically renewing.",
    "governing_law": "A clause stating which state's or country's laws "
                      "govern and are used to interpret the contract.",
    "exclusivity": "A clause granting one party exclusive rights (e.g. the "
                    "only authorized distributor/seller) within some scope.",
}

# Same 7 keys, mapped to their exact column name in CUAD's master_clauses.csv
# (the lawyers' ground-truth answers) — used wherever we need to compare an
# AI's answer against the real one.
CUAD_COLUMN_NAMES = {
    "termination": "Termination For Convenience",
    "liability_cap": "Cap On Liability",
    "non_compete": "Non-Compete",
    "renewal_term": "Renewal Term",
    "renewal_notice": "Notice Period To Terminate Renewal",
    "governing_law": "Governing Law",
    "exclusivity": "Exclusivity",
}

_ENCODING = tiktoken.get_encoding("cl100k_base")

# A rough but consistent token budget per chunk of contract text, chosen so
# one request (chunk + prompt + model's answer) comfortably fits inside the
# tightest free-tier limit we found (Groq's 8,000 tokens/minute).
CHUNK_SIZE_TOKENS = 3000
CHUNK_OVERLAP_TOKENS = 200


def chunk_contract(text: str, chunk_size: int = CHUNK_SIZE_TOKENS,
                    overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Split contract text into overlapping, token-sized pieces.

    Overlap means consecutive chunks share a little text, so a clause that
    happens to straddle a chunk boundary still appears whole in at least one
    chunk.
    """
    tokens = _ENCODING.encode(text)
    if len(tokens) <= chunk_size:
        return [text]

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(tokens), step):
        piece = tokens[start:start + chunk_size]
        chunks.append(_ENCODING.decode(piece))
        if start + chunk_size >= len(tokens):
            break
    return chunks


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def build_prompt(contract_chunk: str) -> str:
    clause_list = "\n".join(
        f'- "{key}": {desc}' for key, desc in CLAUSE_DEFINITIONS.items()
    )
    keys_json_shape = ",\n".join(
        f'  "{key}": {{"present": true or false, "quote": "exact text or null"}}'
        for key in CLAUSE_DEFINITIONS
    )
    return f"""You are reviewing one section of a commercial contract. For each of the \
clause types listed below, decide whether it appears in THIS section of text.

Clause types:
{clause_list}

Rules:
- Only say a clause is present if it actually appears in the text below — \
do not guess or infer from context outside this section.
- If present, "quote" must be the exact text copied from the section \
(word-for-word, no paraphrasing, no added commentary).
- If not present in this section, set "present" to false and "quote" to null.
- Respond with ONLY valid JSON, no other text before or after it, in exactly \
this shape:
{{
{keys_json_shape}
}}

Contract section:
\"\"\"
{contract_chunk}
\"\"\"
"""
