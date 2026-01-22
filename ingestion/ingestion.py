import pandas as pd
from pathlib import Path

# Paths
RAW_DATA_DIR = Path("data/raw_data")
INGESTED_DATA_DIR = Path("data/ingested_data")
LOG_DIR = Path("logs")

INGESTED_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# Column mapping (RAW → CANONICAL)
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

def ingest_csv(file_path: Path) -> pd.DataFrame:

    df = pd.read_csv(file_path, encoding="latin1", low_memory=False)
    
    # Standardize columns
    df = df.rename(columns=COLUMN_MAPPING)
    # Ensure all expected columns exist
    for col in COLUMN_MAPPING.values():
        if col not in df.columns:
            df[col] = None

    # Basic type normalization (NOT cleaning)
    df["isbn"] = df["isbn"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    return df


def run_ingestion():
    for csv_file in RAW_DATA_DIR.glob("*.csv"):
        df = ingest_csv(csv_file)

        output_path = INGESTED_DATA_DIR / csv_file.name
        df.to_csv(output_path, index=False)


if __name__ == "__main__":
    run_ingestion()
