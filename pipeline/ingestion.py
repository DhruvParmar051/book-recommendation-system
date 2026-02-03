"""
CSV Ingestion Script

This script ingests raw CSV files from a specified directory, standardizes
their schema using a predefined column mapping, performs minimal type
normalization, and writes the processed files to an output directory.

This file represents the ingestion stage of an ETL pipeline.
"""

import argparse
import pandas as pd
from pathlib import Path

# ================== COLUMN MAPPING ==================

COLUMN_MAPPING = {
    "Date": "date",
    "Acc. No.": "accession_no",
    "Title": "title",
    "Author/Editor": "author_editor",
    "Ed./Vol.": "edition_volume",
    "Place & Publisher": "place_publisher",
    "ISBN": "isbn",
    "Year": "year",
    "Page(s)": "pages",
    "Source": "source",
    "Class No./Book No.": "class_no_book_no"
}

# ================== INGESTION LOGIC ==================

def ingest_csv(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path, encoding="latin1", low_memory=False)
    df = df.rename(columns=COLUMN_MAPPING)

    # Ensure all expected columns exist
    for col in COLUMN_MAPPING.values():
        if col not in df.columns:
            df[col] = None

    # Basic type normalization (not cleaning)
    df["isbn"] = df["isbn"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    return df


def run_ingestion(input_dir: Path, output_dir: Path) -> None:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return

    for csv_file in csv_files:
        df = ingest_csv(csv_file)
        df.to_csv(output_dir / csv_file.name, index=False)

    print(f"Ingestion complete. Files written to {output_dir}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""CSV INGESTION SCRIPT

PURPOSE
-------
Standardizes raw CSV files into a consistent schema.
This is the ingestion stage of an ETL pipeline.

INPUT
-----
- CSV files from an input directory
- Columns may be inconsistent or missing

PROCESSING
----------
1. Reads all CSV files
2. Renames columns to canonical names
3. Ensures required columns exist
4. Normalizes ISBN and Year types

OUTPUT
------
- Standardized CSV files written to an output directory

NOT INCLUDED
------------
- No data cleaning
- No validation
- No deduplication
- No enrichment
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data/raw_data",
        help="Directory containing raw CSV files (default: data/raw_data)"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/ingested_data",
        help="Directory to write ingested CSV files (default: data/ingested_data)"
    )

    args = parser.parse_args()

    run_ingestion(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
# ================== END OF SCRIPT ==================