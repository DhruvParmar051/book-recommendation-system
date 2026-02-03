"""
Book Recommendation Data Pipeline Runner

This script orchestrates the complete end-to-end DATA PIPELINE
for the book recommendation system.

It sequentially executes all ETL stages that transform raw
library data into clean, enriched, and recommender-ready datasets.

IMPORTANT
---------
This pipeline is strictly limited to data preparation.
It does NOT perform any recommendation logic.

The recommendation system consumes the pipeline output separately.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# ================== FIXED PROJECT PATHS ==================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PIPELINE_DIR = PROJECT_ROOT / "pipeline"
STORAGE_DIR = PROJECT_ROOT / "storage"

INGESTION_SCRIPT = PIPELINE_DIR / "ingestion.py"
CLEAN_SCRIPT = PIPELINE_DIR / "clean.py"
TRANSFORMATION_SCRIPT = PIPELINE_DIR / "transformation.py"
JSON_TO_FEATURES_SCRIPT = PIPELINE_DIR / "json_to_features.py"

# ================== PIPELINE EXECUTION ==================

def run_step(name: str, script_path: Path):
    print(f"STARTING: {name}")

    if not script_path.exists():
        print(f"ERROR: Script not found → {script_path}")
        sys.exit(1)

    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            encoding="utf-8",
            errors="ignore"
        )
    except subprocess.CalledProcessError:
        print(f"ERROR during step: {name}")
        sys.exit(1)

    print(f"COMPLETED: {name}\n")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""BOOK RECOMMENDATION DATA PIPELINE

PURPOSE
-------
Runs the complete ETL pipeline for the book recommendation system.
Transforms raw library data into clean, enriched, and
recommender-ready feature datasets.

PIPELINE STAGES
---------------
1. INGESTION
   - Reads raw CSV files
   - Standardizes schema
   - Outputs ingested CSV files

2. CLEANING
   - Normalizes text and ISBN fields
   - Removes invalid and duplicate records
   - Generates stable record identifiers

3. TRANSFORMATION (ENRICHMENT)
   - Enriches book records using external APIs
   - Fetches authors, subjects, summaries, publisher
   - Outputs enriched canonical JSON

4. FEATURE GENERATION (FINAL)
   - Flattens enriched JSON
   - Extracts recommender-relevant features
   - Writes deterministic feature CSV snapshot

EXECUTION MODEL
---------------
- Steps are executed sequentially
- Pipeline stops immediately on failure
- Uses fixed project directory structure

FINAL OUTPUT
------------
- Canonical enriched JSON:
  data/enriched_data/enriched_books.json

- Recommender-ready feature CSV:
  data/processed_data/books_features.csv

NOT INCLUDED
------------
- No recommendation logic
- No vectorization
- No similarity computation
- No API serving
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.parse_args()  # enables --help

    print("\nBOOK RECOMMENDATION DATA PIPELINE\n")

    run_step("INGESTION", INGESTION_SCRIPT)
    run_step("CLEANING", CLEAN_SCRIPT)
    run_step("TRANSFORMATION (ENRICHMENT)", TRANSFORMATION_SCRIPT)
    run_step("FEATURE GENERATION (JSON → CSV)", JSON_TO_FEATURES_SCRIPT)

    print("PIPELINE FINISHED SUCCESSFULLY\n")
    print("OUTPUT ARTIFACTS")
    print("----------------")
    print("• Enriched JSON  → data/enriched_data/enriched_books.json")
    print("• Feature CSV   → data/processed_data/books_features.csv")

if __name__ == "__main__":
    main()
