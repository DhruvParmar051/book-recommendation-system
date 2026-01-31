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

# ================== FIXED PATHS ==================

RAW_DATA_DIR = Path("data/raw_data")
INGESTED_DATA_DIR = Path("data/ingested_data")

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

    for col in COLUMN_MAPPING.values():
        if col not in df.columns:
            df[col] = None

    df["isbn"] = df["isbn"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    return df


def run_ingestion() -> None:
    INGESTED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for csv_file in RAW_DATA_DIR.glob("*.csv"):
        df = ingest_csv(csv_file)
        df.to_csv(INGESTED_DATA_DIR / csv_file.name, index=False)

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
- CSV files from: data/raw_data/
- Columns may be inconsistent or missing

PROCESSING
----------
1. Reads all CSV files
2. Renames columns to canonical names
3. Ensures required columns exist
4. Normalizes ISBN and Year types

OUTPUT
------
- Standardized CSV files written to:
  data/ingested_data/

NOT INCLUDED
------------
- No data cleaning
- No validation
- No deduplication
- No enrichment
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.parse_args()  # Only for --help
    run_ingestion()


if __name__ == "__main__":
    main()
