import sys
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import requests
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ================== CONFIG ==================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CLEAN_CSV = DATA_DIR / "clean_data" / "clean_books.csv"
OUTPUT_JSON = DATA_DIR / "enriched_data" / "enriched_books.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

MAX_WORKERS = 5              # 🔥 SAFE
BATCH_SIZE = 200             # 🔥 PREVENTS STALL
SAVE_EVERY = 10
LOG_EVERY = 100

# HARD timeouts (connect, read)
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

def load_existing():
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_atomic(data):
    tmp = OUTPUT_JSON.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, OUTPUT_JSON)

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
        # 🔥 NEVER let a thread hang
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

# ================== MAIN ==================

def run_transformation():
    df = pd.read_csv(CLEAN_CSV)

    saved = load_existing()
    seen = {r["book_key"] for r in saved}

    remaining_df = df[
        ~df.apply(lambda r: book_key(r.get("isbn"), r["title"]) in seen, axis=1)
    ]

    total = len(df)
    remaining = len(remaining_df)

    print("🔁 GOOGLE BOOKS ENRICHMENT STARTED (FREEZE-PROOF)")
    print(f"✔ Already processed: {len(seen)}")
    print(f"⏳ Remaining: {remaining}")
    print(f"🚀 Workers: {MAX_WORKERS}")

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
                            save_atomic(saved)
                            print(f"💾 Saved {len(saved)} records")

    except KeyboardInterrupt:
        print("\n⛔ Interrupted! Saving progress…")
        save_atomic(saved)
        return

    save_atomic(saved)
    print(f"✅ COMPLETED. Total processed records: {len(saved)}")

# ================== ENTRY ==================

def main():
    run_transformation()

if __name__ == "__main__":
    main()
