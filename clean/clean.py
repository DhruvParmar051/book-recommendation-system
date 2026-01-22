import pandas as pd
import re
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INGESTED_DIR = DATA_DIR / "ingested_data"
CLEAN_DIR = DATA_DIR / "clean_data"
LOG_DIR = BASE_DIR / "logs"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = CLEAN_DIR / "clean_books.csv"

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



def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    # Normalize text columns
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

    # Normalize ISBN
    if "isbn" in df.columns:
        df["isbn"] = df["isbn"].apply(normalize_isbn)

    # Drop rows without title
    before = len(df)
    df = df[df["title"].notna()]
    

    before = len(df)

    with_isbn = df[df["isbn"].notna()]
    without_isbn = df[df["isbn"].isna()]

    with_isbn = with_isbn.drop_duplicates(subset=["isbn"], keep="first")
    without_isbn = without_isbn.drop_duplicates(
        subset=["title", "author_editor"], keep="first"
    )

    df = pd.concat([with_isbn, without_isbn], ignore_index=True)


    # Year sanity
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df.loc[(df["year"] < 1500) | (df["year"] > 2035), "year"] = None

    # Stable record_id
    df["record_id"] = df.apply(make_record_id, axis=1)

    return df



def main():
    print("Starting cleaning step")

    all_files = list(INGESTED_DIR.glob("*.csv"))
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
    cleaned_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Clean data saved to {OUTPUT_CSV}\nTotal cleaned rows: {len(cleaned_df)}")

if __name__ == "__main__":
    main()
