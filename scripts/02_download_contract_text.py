"""
Stage 3 setup: download the full contract text for our 130 sampled contracts.

The master_clauses.csv from Stage 1 only has the lawyer's extracted clause
answers (that's our ground truth/answer key) — we also need the raw,
un-annotated contract text to actually send to the AI models, since giving
them the answer key would defeat the point.

We pull from CUAD's official Zenodo archive (not the Hugging Face mirror,
which turned out to only include 200 of the 510 contract text files). A
handful of filenames in master_clauses.csv don't exactly match the archive
(stray trailing spaces, "&" replaced with "_") — FILENAME_FIXES below maps
those by hand, found once during Stage 3 setup.
"""
import csv
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

SAMPLE_CSV = "data/processed/sample_contracts.csv"
OUT_DIR = Path("data/raw/full_contract_txt")
ZENODO_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"

# CSV filename (after swapping .PDF -> .txt) -> actual filename in the archive.
FILENAME_FIXES = {
    "Principal Life Insurance Company - Broker Dealer Marketing and Servicing Agreement .txt":
        "Principal Life Insurance Company - Broker Dealer Marketing and Servicing Agreement.txt",
    "MOELIS&CO_03_24_2014-EX-10.19-STRATEGIC ALLIANCE AGREEMENT.txt":
        "MOELIS_CO_03_24_2014-EX-10.19-STRATEGIC ALLIANCE AGREEMENT.txt",
    "PACIRA PHARMACEUTICALS, INC. - A&R STRATEGIC LICENSING, DISTRIBUTION AND MARKETING AGREEMENT .txt":
        "PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC LICENSING, DISTRIBUTION AND MARKETING AGREEMENT .txt",
    "ELECTRAMECCANICA VEHICLES CORP. - Manufacturing Agreement .txt":
        "ELECTRAMECCANICA VEHICLES CORP. - Manufacturing Agreement.txt",
    "NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO THE DISTRIBUTOR AGREEMENT BETWEEN INGRAM MICRO AND NETGEAR-.txt":
        "NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO THE DISTRIBUTOR AGREEMENT BETWEEN INGRAM MICRO AND NETGEAR.txt",
}


def wanted_filenames() -> list[str]:
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row["Filename"].rsplit(".", 1)[0] + ".txt" for row in rows]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = wanted_filenames()
    already = {p.name for p in OUT_DIR.glob("*.txt")}
    missing = [name for name in wanted if name not in already]

    if not missing:
        print(f"All {len(wanted)} contract text files already present in {OUT_DIR}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "CUAD_v1.zip"
        print(f"Downloading CUAD_v1.zip (~106MB) from Zenodo...")
        resp = requests.get(ZENODO_URL, timeout=120)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)

        print("Extracting full_contract_txt/ ...")
        with zipfile.ZipFile(zip_path) as zf:
            members = [m for m in zf.namelist() if "/full_contract_txt/" in m and m.endswith(".txt")]
            zf.extractall(tmp, members=members)

        extracted_dir = Path(tmp) / "CUAD_v1" / "full_contract_txt"
        ok, still_missing = 0, []
        for name in missing:
            archive_name = FILENAME_FIXES.get(name, name)
            src = extracted_dir / archive_name
            if src.exists():
                shutil.copy(src, OUT_DIR / name)
                ok += 1
            else:
                still_missing.append(name)

        print(f"Copied {ok}/{len(missing)} newly-needed files.")
        if still_missing:
            print(f"Still missing ({len(still_missing)}):")
            for name in still_missing:
                print(f"  - {name}")

    print(f"\n{len(wanted) - len(still_missing)}/{len(wanted)} contract text files now in {OUT_DIR}")


if __name__ == "__main__":
    main()
