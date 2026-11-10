"""
Stage 1: pick which clause types to study and which contracts to sample.

Reads the CUAD master clauses CSV (download instructions in README.md),
counts how many contracts actually contain each candidate clause type,
then draws a reproducible random sample of contracts for the rest of the
project to use.
"""
import pandas as pd

RAW_CSV = "data/raw/master_clauses.csv"
SAMPLE_OUT = "data/processed/sample_contracts.csv"
SAMPLE_SIZE = 130
RANDOM_SEED = 42

# Our 6 clause types, mapped to CUAD's exact column names.
CLAUSE_TYPES = {
    "termination": "Termination For Convenience",
    "liability_cap": "Cap On Liability",
    "non_compete": "Non-Compete",
    "renewal_term": "Renewal Term",
    "renewal_notice": "Notice Period To Terminate Renewal",
    "governing_law": "Governing Law",
    "exclusivity": "Exclusivity",
}


def is_present(series: pd.Series) -> pd.Series:
    """A clause column holds a quoted-text list like "['...']", or '[]' if absent."""
    return series.fillna("[]") != "[]"


def main() -> None:
    df = pd.read_csv(RAW_CSV)
    total = len(df)
    print(f"Full dataset: {total} contracts")

    print("\nHow often each clause type appears in the full 510 contracts:")
    for label, col in CLAUSE_TYPES.items():
        count = is_present(df[col]).sum()
        print(f"  {label:20s} {count:3d}/{total} ({count/total:.1%})")

    sample = df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED)

    print(f"\nHow often each clause type appears in our {SAMPLE_SIZE}-contract sample "
          f"(seed={RANDOM_SEED}):")
    for label, col in CLAUSE_TYPES.items():
        count = is_present(sample[col]).sum()
        print(f"  {label:20s} {count:3d}/{SAMPLE_SIZE} ({count/SAMPLE_SIZE:.1%})")

    sample[["Filename", "Document Name"]].to_csv(SAMPLE_OUT, index=False)
    print(f"\nSaved sample contract list to {SAMPLE_OUT}")


if __name__ == "__main__":
    main()
