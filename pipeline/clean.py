"""
CSV Cleaning Script

This script performs the cleaning stage of a data pipeline.
It takes ingested CSV files, normalizes text fields, validates ISBNs,
removes duplicates, applies sanity checks, and produces a single
cleaned dataset ready for downstream use.
"""

import argparse
import pandas as pd
import re
import hashlib
from pathlib import Path

# ================== NORMALIZATION HELPERS ==================

def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_isbn(value):
    if pd.isna(value):
        return None
    isbn = re.sub(r"[^0-9Xx]", "", str(value)).upper()
    return isbn if len(isbn) in (10, 13) else None


def safe_str(value):
    return "" if pd.isna(value) else str(value)


def make_record_id(row):
    key = (
        safe_str(row.get("title")) + "|" +
        safe_str(row.get("author_editor")) + "|" +
        safe_str(row.get("isbn"))
    )
    return hashlib.md5(key.encode("utf-8")).hexdigest()

# ================== CLEANING LOGIC ==================

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize the ingested DataFrame.
    """

    TEXT_COLUMNS = [
        "title",
        "author_editor",
        "edition_volume",
        "place_publisher",
        "source",
        "class_no_book_no"
    ]

    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    if "isbn" in df.columns:
        df["isbn"] = df["isbn"].apply(normalize_isbn)

    df = df[df["title"].notna()]

    with_isbn = df[df["isbn"].notna()]
    without_isbn = df[df["isbn"].isna()]

    with_isbn = with_isbn.drop_duplicates(subset=["isbn"], keep="first")
    without_isbn = without_isbn.drop_duplicates(
        subset=["title", "author_editor"], keep="first"
    )

    df = pd.concat([with_isbn, without_isbn], ignore_index=True)

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df.loc[(df["year"] < 1500) | (df["year"] > 2035), "year"] = None

    df["record_id"] = df.apply(make_record_id, axis=1)

    return df

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""CSV CLEANING SCRIPT

PURPOSE
-------
Cleans and consolidates ingested CSV data into a single,
high-quality dataset suitable for analytics or ML.

INPUT
-----
- CSV files from an input directory
- Data already standardized by ingestion step

CLEANING OPERATIONS
-------------------
1. Normalize text fields (lowercase, trim, whitespace fix)
2. Normalize and validate ISBN values
3. Remove rows without titles
4. Deduplicate records:
   - Prefer ISBN-based deduplication
   - Fall back to (title, author) when ISBN is missing
5. Apply year sanity checks (1500–2035)
6. Generate stable record_id using hashing

OUTPUT
------
- Single cleaned CSV written to an output file

NOT INCLUDED
------------
- No external enrichment
- No fuzzy matching
- No database insertion
- No ML feature engineering
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("../data/ingested_data"),
        help="Directory containing ingested CSV files (default: data/ingested_data)"
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("../data/clean_data/clean_books.csv"),
        help="Path to write cleaned CSV (default: data/clean_data/clean_books.csv)"
    )

    args = parser.parse_args()

    print("Starting cleaning step")

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    all_files = list(args.input_dir.glob("*.csv"))
    if not all_files:
        print("No ingested CSV files found")
        return

    dfs = []
    for file in all_files:
        df = pd.read_csv(file, encoding="latin1", low_memory=False)
        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(combined_df)} ingested rows")

    cleaned_df = clean_dataframe(combined_df)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(args.output_file, index=False)

    print(f"Clean data saved to {args.output_file}")
    print(f"Total cleaned rows: {len(cleaned_df)}")


if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================