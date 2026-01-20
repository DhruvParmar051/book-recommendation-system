import pandas as pd
import aiohttp
import asyncio
import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV_PATH = DATA_DIR / "raw_data" / "Accession Register-Books.csv"
OUTPUT_JSON_PATH = DATA_DIR / "ingested_data" / "books_raw_enriched.json"

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
CONCURRENCY_LIMIT = 20
SAVE_EVERY = 100

def normalize_title(title):
    if not title or pd.isna(title):
        return None
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title

def clean_isbn(isbn):
    if pd.isna(isbn):
        return None
    isbn = str(isbn)
    if "e+" in isbn.lower():
        return None
    isbn = isbn.replace(".0", "")
    isbn = re.sub(r"[^0-9Xx]", "", isbn).upper()
    if len(isbn) in (10, 13):
        return isbn
    return None

async def search_openlibrary_async(session, params):
    try:
        headers = {"User-Agent": "BookRecommendationSystem/1.0"}
        async with session.get(OPENLIBRARY_SEARCH_URL, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("numFound", 0) > 0:
                    return data["docs"][0]
    except Exception:
        pass
    return None

async def fetch_book_details_smart_async(session, title, author):
    res = await search_openlibrary_async(
        session, {"title": title, "author": author, "limit": 1}
    )
    if res:
        return res, "Strict match"

    if ":" in title:
        short_title = title.split(":")[0].strip()
        res = await search_openlibrary_async(
            session, {"title": short_title, "author": author, "limit": 1}
        )
        if res:
            return res, "Short title + author"

    res = await search_openlibrary_async(
        session, {"title": title, "limit": 1}
    )
    if res:
        return res, "Title-only"

    return None, "Not found"

enriched_books = []
processed_book_keys = set()
processed_count = 0

def load_existing_progress():
    if not OUTPUT_JSON_PATH.exists():
        return [], set()

    with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rebuilt_keys = set()
    cleaned_data = []

    for item in data:
        title = item.get("original_title")
        isbn = item.get("isbn")

        norm_title = normalize_title(title)
        if not norm_title:
            continue

        book_key = item.get("book_key")
        if not book_key:
            book_key = f"{isbn}|{norm_title}"
            item["book_key"] = book_key

        rebuilt_keys.add(book_key)
        cleaned_data.append(item)

    return cleaned_data, rebuilt_keys

def save_progress():
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_JSON_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(enriched_books, f, indent=2)
    os.replace(tmp, OUTPUT_JSON_PATH)

async def process_row(session, semaphore, row, index, total):
    global processed_count

    title = row.get("Title", "")
    author = row.get("Author/Editor", "")
    isbn = clean_isbn(row.get("ISBN"))
    norm_title = normalize_title(title)

    if not norm_title:
        return

    book_key = f"{isbn}|{norm_title}"

    if book_key in processed_book_keys:
        return

    async with semaphore:
        result, method = await fetch_book_details_smart_async(session, title, author)

        if not result:
            return

        enriched_books.append({
            "book_key": book_key,
            "isbn": isbn,
            "original_title": title,
            "original_author": author,
            "api_data": result,
            "match_method": method,
            "found": True
        })

        processed_book_keys.add(book_key)
        processed_count += 1

        print(f"[{index+1}/{total}] FOUND : {title[:50]}")

        if processed_count % SAVE_EVERY == 0:
            save_progress()
            print(f"Saved {len(enriched_books)} records")

async def ingest_books_async():
    global enriched_books, processed_book_keys

    print(f"Reading CSV from {RAW_CSV_PATH}")
    df = pd.read_csv(RAW_CSV_PATH, encoding="latin1", low_memory=False)
    df.drop_duplicates(subset=["Title", "Author/Editor", "ISBN"], inplace=True)
    enriched_books, processed_book_keys = load_existing_progress()

    print(f"Resuming with {len(enriched_books)} books already saved")
    print(f"Starting async ingestion (concurrency={CONCURRENCY_LIMIT})")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []

    async with aiohttp.ClientSession() as session:
        for index, row in df.iterrows():
            tasks.append(
                process_row(session, semaphore, row, index, len(df))
            )

        await asyncio.gather(*tasks)

    save_progress()
    print(f"Ingestion complete. Total books saved: {len(enriched_books)}")

def main():
    asyncio.run(ingest_books_async())

if __name__ == "__main__":
    main()
