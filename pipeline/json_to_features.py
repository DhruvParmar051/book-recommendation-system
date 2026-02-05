"""
JSON to Feature Converter

This module converts enriched book metadata stored in JSON format into a
flattened, recommender-ready feature table (CSV).

It represents the FINAL stage of the ETL pipeline and serves as the
contract boundary between the data pipeline and the recommendation system.

DESIGN PRINCIPLES
-----------------
1. Preserve pipeline–recommender separation
2. Flatten nested and list-based fields
3. Freeze a stable schema for downstream consumers
4. Avoid embedding recommendation logic

THIS MODULE IS RESPONSIBLE FOR
------------------------------
- Reading enriched JSON data
- Flattening nested structures (lists, dicts)
- Selecting recommender-relevant features
- Writing a deterministic CSV snapshot

THIS MODULE IS NOT RESPONSIBLE FOR
---------------------------------
- Data ingestion
- Data cleaning
- Metadata enrichment
- Vectorization
- Recommendation logic
"""

import argparse
import json
import pandas as pd
from pathlib import Path


# ================== FEATURE CONFIG ==================

FEATURE_COLUMNS = [
    "record_id",
    "title",
    "class_no_book_no",
    "intent",
    "depth",
    "publisher",
    "pages"
]


# ================== CONVERSION LOGIC ==================

def flatten_enriched_json(
    input_path: Path,
    output_path: Path
) -> None:
    """
    Convert enriched JSON data into a flattened feature CSV.

    Parameters
    ----------
    input_path : Path
        Path to enriched JSON file (canonical dataset).

    output_path : Path
        Path where the feature CSV will be written.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Enriched JSON not found: {input_path}")

    # Load enriched JSON
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # ------------------
    # Flatten list fields
    # ------------------
    for col in ["authors", "subjects"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else None
            )

    # ------------------
    # Flatten signal fields
    # ------------------
    if "signals" in df.columns:
        df["intent"] = df["signals"].apply(
            lambda x: x.get("intent") if isinstance(x, dict) else None
        )
        df["depth"] = df["signals"].apply(
            lambda x: x.get("depth") if isinstance(x, dict) else None
        )
    else:
        df["intent"] = None
        df["depth"] = None

    # ------------------
    # Ensure required feature columns
    # ------------------
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[FEATURE_COLUMNS]

    # Write output CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Feature CSV written to: {output_path}")
    print(f"Rows processed: {len(df)}")


# ================== CLI INTERFACE ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""JSON TO FEATURE CONVERTER

PURPOSE
-------
Convert enriched book metadata from JSON into a flattened feature CSV
for consumption by the recommendation engine.

INPUT
-----
- Enriched JSON file produced by the data pipeline

PROCESSING
----------
1. Load enriched JSON data
2. Flatten list-based fields (authors, subjects)
3. Extract signal fields (intent, depth)
4. Select and order recommender-relevant columns
5. Write a deterministic CSV snapshot

OUTPUT
------
- Flat CSV file containing recommender-ready features

NOT INCLUDED
------------
- Data ingestion
- Data cleaning
- Metadata enrichment
- Vectorization
- Recommendation logic
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    project_root = Path(__file__).resolve().parent.parent

    parser.add_argument(
        "--input-path",
        type=Path,
        default=project_root / "data" / "enriched_data" / "enriched_books.json",
        help="Path to enriched JSON file (default: data/enriched_data/enriched_books.json)"
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        default=project_root / "data" / "processed_data" / "books_features.csv",
        help="Path to output feature CSV (default: data/processed_data/books_features.csv)"
    )

    args = parser.parse_args()

    flatten_enriched_json(
        input_path=args.input_path,
        output_path=args.output_path
    )


if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================
