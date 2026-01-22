import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INGESTION_SCRIPT = BASE_DIR / r"ingestion\ingestion.py"
CLEAN_SCRIPT = BASE_DIR / r"clean\clean.py"
TRANSFORMATION_SCRIPT = BASE_DIR / r"transformation\transformation.py"


def run_step(name: str, script_path: Path):
    print(f"STARTING: {name}")

    if not script_path.exists():
        print(f"ERROR: {script_path} not found")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)
        
    

    if result.returncode != 0:
        print("ERROR occurred")
        print(result.stderr)
        sys.exit(1)

    print(f"COMPLETED: {name}")


def main():
    print("BOOK RECOMMENDATION DATA PIPELINE")

    run_step("INGESTION", INGESTION_SCRIPT)
    run_step("CLEANING", CLEAN_SCRIPT)
    run_step("TRANSFORMATION (OPAC ENRICHMENT)", TRANSFORMATION_SCRIPT)

    print("PIPELINE FINISHED SUCCESSFULLY")
    print("Final output → data/enriched_data/enriched_book.json")

if __name__ == "__main__":
    main()
