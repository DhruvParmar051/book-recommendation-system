import pandas as pd
import aiohttp
import asyncio
import json
import os
import re
from pathlib import Path

# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RAW_CSV_PATH = DATA_DIR / "raw_data" / "Accession Register-Books.csv"
OUTPUT_JSON_PATH = DATA_DIR / "ingested_data" / "books_enriched.json"

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

CONCURRENCY_LIMIT = 10
SAVE_EVERY = 100

USER_AGENT = "BookRecommendationSystem/1.0 (academic-use)"

# =========================
# NORMALIZATION HELPERS
# =========================

def normalize_title(title: str) -> str | None:
    if not title or pd.isna(title):
        return None
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title

def clean_isbn(isbn) -> str | None:
    if not isbn or pd.isna(isbn):
        return None
    isbn = str(isbn).replace(".0", "")
    isbn = re.sub(r"[^0-9Xx]", "", isbn).upper()
    if len(isbn) in (10, 13):
        return isbn
    return None

def make_book_key(isbn, title):
    return f"{isbn}|{normalize_title(title)}"

# =========================
# OPENLIBRARY SEARCH
# =========================

async def search_openlibrary(session, params):
    headers = {"User-Agent": USER_AGENT}
    try:
        async with session.get(
            OPENLIBRARY_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("numFound", 0) > 0:
                    return data["docs"][0]
    except Exception:
        pass
    return None

async def fetch_book(session, title, author=None):
    # 1. Strict title + author
    if author:
        res = await search_openlibrary(
            session, {"title": title, "author": author, "limit": 1}
        )
        if res:
            return res, "Strict match"

    # 2. Short title
    if ":" in title:
        short = title.split(":")[0].strip()
        res = await search_openlibrary(
            session, {"title": short, "limit": 1}
        )
        if res:
            return res, "Short title match"

    # 3. Title only
    res = await search_openlibrary(
        session, {"title": title, "limit": 1}
    )
    if res:
        return res, "Title-only match"

    return None, None

# =========================
# FILE HANDLING
# =========================

def load_existing():
    if OUTPUT_JSON_PATH.exists():
        with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_atomic(data):
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_JSON_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, OUTPUT_JSON_PATH)

# =========================
# PROCESS SINGLE ROW
# =========================

async def process_row(session, semaphore, row, total, idx, saved, seen_keys):
    async with semaphore:
        title = str(row.get("Title", "")).strip()
        author = str(row.get("Author/Editor", "")).strip()
        isbn = clean_isbn(row.get("ISBN"))

        if not title:
            return

        book_key = make_book_key(isbn, title)

        if book_key in seen_keys:
            return

        result, method = await fetch_book(session, title, author)

        status = "FOUND" if result else "MISSING"
        print(f"[{idx}/{total}] {status} : {title[:50]}")

        if not result:
            return  #

        saved.append({
            "book_key": book_key,
            "isbn": isbn,
            "original_title": title,
            "original_author": author,
            "api_data": result,
            "match_method": method
        })

        seen_keys.add(book_key)

        if len(saved) % SAVE_EVERY == 0:
            save_atomic(saved)
            print(f"Saved {len(saved)} books")

        await asyncio.sleep(0.1)



async def ingest_books_async():
    print(f"Reading CSV: {RAW_CSV_PATH}")
    df = pd.read_csv(RAW_CSV_PATH, encoding="latin1", low_memory=False)
    df.drop_duplicates(subset=["Title", "Author/Editor", "ISBN"], inplace=True)
    saved = load_existing()
    seen_keys = {b["book_key"] for b in saved}

    print(f"Resuming with {len(saved)} books already saved")
    print(f"Starting async ingestion (concurrency={CONCURRENCY_LIMIT})")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []

    async with aiohttp.ClientSession() as session:
        for idx, row in df.iterrows():
            tasks.append(
                process_row(
                    session,
                    semaphore,
                    row,
                    len(df),
                    idx + 1,
                    saved,
                    seen_keys
                )
            )

        completed = 0
        for coro in asyncio.as_completed(tasks):
            try:
                await coro
                completed += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Task error: {e}")

    save_atomic(saved)
    print(f"\nIngestion complete. Total books saved: {len(saved)}")

# =========================
# ENTRY POINT
# =========================

def main():
    try:
        asyncio.run(ingest_books_async())
    except KeyboardInterrupt:
        print("\nInterrupted safely. Progress saved.")

if __name__ == "__main__":
    main()
