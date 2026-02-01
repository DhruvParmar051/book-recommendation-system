"""
Book Recommendation Data Pipeline Runner

This script orchestrates the complete end-to-end data pipeline
for the book recommendation system. It sequentially executes
all pipeline stages using fixed project paths.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# ================== FIXED PATHS ==================

BASE_DIR = Path(__file__).resolve().parent

INGESTION_SCRIPT = BASE_DIR / "pipeline" / "ingestion.py"
CLEAN_SCRIPT = BASE_DIR / "pipeline" / "clean.py"
TRANSFORMATION_SCRIPT = BASE_DIR / "pipeline" / "transformation.py"
STORAGE_SCRIPT = BASE_DIR / "storage" / "db.py"

# ================== PIPELINE EXECUTION ==================

def run_step(name: str, script_path: Path):
    print(f"STARTING: {name}")

    if not script_path.exists():
        print(f"ERROR: {script_path} not found")
        sys.exit(1)

    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            encoding="utf-8",
            errors="ignore"
        )
    except subprocess.CalledProcessError:
        print(f"ERROR during {name}")
        sys.exit(1)

    print(f"COMPLETED: {name}\n")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""BOOK RECOMMENDATION DATA PIPELINE

PURPOSE
-------
Runs the complete end-to-end data pipeline for the
book recommendation system.

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
   - Enriches book records using Google Books API
   - Fetches authors, subjects, summaries, publisher
   - Saves results incrementally as JSON

4. STORAGE
   - Loads enriched JSON into SQLite database
   - Creates database schema
   - Ignores duplicate records safely

EXECUTION MODEL
---------------
- Steps are executed sequentially
- Pipeline stops immediately on failure
- Uses fixed project directory structure

FINAL OUTPUT
------------
- SQLite database created at:
  data/storage_data/books.sqlite

NOT INCLUDED
------------
- No parallel step execution
- No partial step selection
- No retry logic between stages
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.parse_args()  # enables --help

    print("BOOK RECOMMENDATION DATA PIPELINE\n")

    run_step("INGESTION", INGESTION_SCRIPT)
    run_step("CLEANING", CLEAN_SCRIPT)
    run_step("TRANSFORMATION (OPAC ENRICHMENT)", TRANSFORMATION_SCRIPT)
    run_step("STORAGE (JSON → SQLITE)", STORAGE_SCRIPT)

    print("PIPELINE FINISHED SUCCESSFULLY")
    print("Final output → data/storage_data/books.sqlite")

if __name__ == "__main__":
    main()
