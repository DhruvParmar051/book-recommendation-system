"""
CSV Enrichment Script

This script performs the enrichment stage of a data pipeline.
It takes cleaned book records and enriches them using the
Google Books API to fetch metadata such as authors, subjects,
publisher, and summaries.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import pandas as pd
import requests
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ================== API CONFIG ==================

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

MAX_WORKERS = 5
BATCH_SIZE = 200
SAVE_EVERY = 10
LOG_EVERY = 100

TIMEOUT = (2, 2)

HEADERS = {
    "User-Agent": "BookRecommendationSystem/1.0"
}

# ================== HELPERS ==================

def clean_text(text):
    if not text or pd.isna(text):
        return None
    return re.sub(r"\s+", " ", str(text).strip())


def book_key(isbn, title):
    isbn = isbn or "NOISBN"
    return f"{isbn}|{title.lower()}"


def load_existing(output_json: Path):
    if output_json.exists():
        with open(output_json, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_atomic(data, output_json: Path):
    tmp = output_json.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, output_json)

# ================== GOOGLE BOOKS ==================

def query_google_books(session, params):
    try:
        r = session.get(
            GOOGLE_BOOKS_API,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        data = r.json()

        if "items" not in data:
            return None

        return data["items"][0]["volumeInfo"]

    except Exception:
        return None


def search_by_isbn(session, isbn):
    isbn = re.sub(r"[^0-9Xx]", "", str(isbn))
    return query_google_books(session, {"q": f"isbn:{isbn}"})


def search_by_title_author(session, title, author):
    q = title
    if author:
        q += f"+inauthor:{author}"
    return query_google_books(session, {"q": q})


def extract_book_info(info):
    return {
        "title": clean_text(info.get("title")),
        "authors": info.get("authors"),
        "isbn": next(
            (i["identifier"] for i in info.get("industryIdentifiers", [])
             if i["type"] in ("ISBN_13", "ISBN_10")),
            None
        ),
        "year": info.get("publishedDate"),
        "subjects": info.get("categories"),
        "summary": clean_text(info.get("description")),
        "publisher": info.get("publisher"),
    }

# ================== WORKER ==================

def process_row(row, session):
    title = row["title"]
    isbn = row.get("isbn")
    author = row.get("authors")

    key = book_key(isbn, title)

    info = None
    if isbn:
        info = search_by_isbn(session, isbn)

    if not info:
        info = search_by_title_author(session, title, author)

    if not info:
        return {
            "record_id": row["record_id"],
            "book_key": key,
            "status": "MISSING",
            "accession_no": row.get("accession_no"),
            "class_no_book_no": row.get("class_no_book_no"),
            "pages": row.get("pages"),
            "title": title,
            "authors": author,
            "isbn": isbn,
            "year": None,
            "subjects": None,
            "summary": None,
            "publisher": None,
        }

    book = extract_book_info(info)

    return {
        "record_id": row["record_id"],
        "book_key": key,
        "status": "FOUND",
        "accession_no": row.get("accession_no"),
        "class_no_book_no": row.get("class_no_book_no"),
        "pages": row.get("pages"),
        "title": book["title"],
        "authors": book["authors"],
        "isbn": book["isbn"],
        "year": book["year"],
        "subjects": book["subjects"],
        "summary": book["summary"],
        "publisher": book["publisher"],
    }

# ================== MAIN LOGIC ==================

def run_transformation(input_csv: Path, output_json: Path):
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_json.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)

    saved = load_existing(output_json)
    seen = {r["book_key"] for r in saved}

    remaining_df = df[
        ~df.apply(lambda r: book_key(r.get("isbn"), r["title"]) in seen, axis=1)
    ]

    total = len(df)
    remaining = len(remaining_df)

    print("GOOGLE BOOKS ENRICHMENT STARTED")
    print(f"Already processed: {len(seen)}")
    print(f"Remaining: {remaining}")
    print(f"Workers: {MAX_WORKERS}")

    lock = Lock()
    session = requests.Session()
    rows = list(remaining_df.iterrows())

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for start in range(0, len(rows), BATCH_SIZE):
                batch = rows[start:start + BATCH_SIZE]

                futures = [
                    executor.submit(process_row, row, session)
                    for _, row in batch
                ]

                for future in as_completed(futures):
                    result = future.result()

                    with lock:
                        saved.append(result)
                        seen.add(result["book_key"])

                        if len(saved) % LOG_EVERY == 0:
                            title = result.get("title") or ""
                            print(f"[{len(saved)}/{total}] {result['status']} : {title[:50]}")

                        if len(saved) % SAVE_EVERY == 0:
                            save_atomic(saved, output_json)
                            print(f"Saved {len(saved)} records")

    except KeyboardInterrupt:
        print("\nInterrupted! Saving progress…")
        save_atomic(saved, output_json)
        return

    save_atomic(saved, output_json)
    print(f"COMPLETED. Total processed records: {len(saved)}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""CSV ENRICHMENT SCRIPT (GOOGLE BOOKS API)

PURPOSE
-------
Enrich cleaned book records with metadata from Google Books API.
This is the transformation/enrichment stage of the pipeline.

INPUT
-----
- Cleaned CSV file

ENRICHMENT PROCESS
------------------
1. Load cleaned book records
2. Skip already-enriched books (resume-safe)
3. Query Google Books API using:
   - ISBN (preferred)
   - Title + Author (fallback)
4. Fetch metadata:
   - Authors
   - ISBN
   - Published year
   - Subjects
   - Summary
   - Publisher
5. Process records concurrently
6. Save results incrementally

OUTPUT
------
- JSON file containing enriched records

FAILURE HANDLING
----------------
- Missing API results marked as MISSING
- Safe retries via resume
- Interrupt-safe saving

NOT INCLUDED
------------
- No paid API usage
- No database insertion
- No recommendation logic
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("../data/clean_data/clean_books.csv"),
        help="Path to cleaned CSV file (default: data/clean_data/clean_books.csv)"
    )

    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("../data/enriched_data/enriched_books.json"),
        help="Path to write enriched JSON (default: data/enriched_data/enriched_books.json)"
    )

    args = parser.parse_args()

    run_transformation(args.input_csv, args.output_json)


if __name__ == "__main__":
    main()
# ================== END OF SCRIPT ==================