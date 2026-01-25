import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INGESTION_SCRIPT = BASE_DIR / r"ingestion\ingestion.py"
CLEAN_SCRIPT = BASE_DIR / r"clean\clean.py"
TRANSFORMATION_SCRIPT = BASE_DIR / r"transformation\transformation.py"
STORAGE_SCRIPT = BASE_DIR / r"storage\db.py"

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
    except subprocess.CalledProcessError as e:
        print("ERROR occurred")
        sys.exit(1)

    print(f"COMPLETED: {name}\n")


def main():
    print("BOOK RECOMMENDATION DATA PIPELINE\n")

    run_step("INGESTION", INGESTION_SCRIPT)
    run_step("CLEANING", CLEAN_SCRIPT)
    run_step("TRANSFORMATION (OPAC ENRICHMENT)", TRANSFORMATION_SCRIPT)
    run_step("STORAGE (JSON → SQLITE)", STORAGE_SCRIPT)
    print("PIPELINE FINISHED SUCCESSFULLY")
    print("Final output → data/storage_data/books.sqlite")
if __name__ == "__main__":
    main()
