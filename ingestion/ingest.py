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

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CONCURRENCY_LIMIT = 20

def clean_isbn(isbn):
    if pd.isna(isbn):
        return None
    isbn = str(isbn).replace(".0", "")
    isbn = re.sub(r"[^0-9Xx]", "", isbn).upper()
    if len(isbn) in (10, 13):
        return isbn
    return None

async def search_openalex(session, params):
    headers = {"User-Agent": "BookRecommendationSystem/1.0"}
    try:
        async with session.get(OPENALEX_WORKS_URL, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    return results[0]
    except Exception:
        pass
    return None

async def fetch_openalex_by_isbn(session, isbn):
    return await search_openalex(session, {"filter": f"isbn:{isbn}"})

async def fetch_openalex_by_title_author(session, title, author=None):
    query = title
    if author:
        query += f" {author}"
    return await search_openalex(session, {"search": query})

enriched_books = []
processed_ids = set()
processed_count = 0

def load_existing_progress():
    if OUTPUT_JSON_PATH.exists():
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Corrupted JSON file detected. Fix before continuing.")
            exit(1)
    return []

def save_progress():
    temp_path = OUTPUT_JSON_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(enriched_books, f, indent=4)
    os.replace(temp_path, OUTPUT_JSON_PATH)

async def process_row(session, semaphore, row, index, total):
    global processed_count

    local_id = str(row.get("Acc. No.", index))
    if local_id in processed_ids:
        return

    title = str(row.get("Title", "")).strip()
    author = str(row.get("Author/Editor", "")).strip()
    isbn = clean_isbn(row.get("ISBN"))

    async with semaphore:
        result = None
        method = "not_found"
        confidence = "low"

        if isbn:
            result = await fetch_openalex_by_isbn(session, isbn)
            if result:
                method = "openalex_isbn"
                confidence = "high"

        if not result and title:
            result = await fetch_openalex_by_title_author(session, title, author)
            if result:
                method = "openalex_title_author"
                confidence = "medium"

        if not result and title:
            result = await fetch_openalex_by_title_author(session, title)
            if result:
                method = "openalex_title_only"
                confidence = "low"

        status = "FOUND" if result else "MISSING"
        print(f"[{index+1}/{total}] {status} : {title[:40]}")

        enriched_books.append({
            "local_id": local_id,
            "isbn": isbn,
            "original_title": title,
            "original_author": author,
            "api_data": result,
            "found": bool(result),
            "match_method": method,
            "confidence": confidence,
            "source": "openalex"
        })

        processed_ids.add(local_id)
        processed_count += 1

        if processed_count % 100 == 0:
            save_progress()
            print(f"Saved {len(enriched_books)} records")

        await asyncio.sleep(0.2)

async def ingest_books_async():
    global enriched_books, processed_ids

    print(f"Reading CSV from {RAW_CSV_PATH}")
    df = pd.read_csv(RAW_CSV_PATH, encoding="latin1", low_memory=False)

    enriched_books = load_existing_progress()
    processed_ids = {str(x["local_id"]) for x in enriched_books}

    print(f"Resuming with {len(enriched_books)} records processed")
    print(f"Starting OpenAlex ingestion with concurrency={CONCURRENCY_LIMIT}")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = []

    async with aiohttp.ClientSession() as session:
        for index, row in df.iterrows():
            local_id = str(row.get("Acc. No.", index))
            if local_id in processed_ids:
                continue
            tasks.append(process_row(session, semaphore, row, index, len(df)))

        if tasks:
            await asyncio.gather(*tasks)

    save_progress()
    print(f"Ingestion complete. Total records: {len(enriched_books)}")

def main():
    asyncio.run(ingest_books_async())

if __name__ == "__main__":
    main()
