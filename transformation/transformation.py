import pandas as pd
import aiohttp
import asyncio
import json
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CLEAN_CSV = DATA_DIR / "clean_data" / "clean_books.csv"
OUTPUT_JSON = DATA_DIR / "enriched_data" / "enriched_books.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://opac.daiict.ac.in/cgi-bin/koha/opac-search.pl"
DETAIL_URL = "https://opac.daiict.ac.in/cgi-bin/koha/opac-detail.pl"

CONCURRENCY = 15
SAVE_EVERY = 100
HEADERS = {"User-Agent": "AcademicBookCrawler/1.0"}


def clean_text(text):
    if not text or pd.isna(text):
        return None
    return re.sub(r"\s+", " ", text.strip())

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
        json.dump(data, f, indent=2)
    os.replace(tmp, OUTPUT_JSON)

async def search_opac(session, isbn, title):
    params = {"idx": "nb", "q": isbn} if isbn else {"idx": "ti", "q": title}

    async with session.get(SEARCH_URL, params=params, headers=HEADERS) as r:
        soup = BeautifulSoup(await r.text(), "html.parser")

    link = soup.select_one("a[href*='opac-detail.pl']")
    if link and "biblionumber=" in link["href"]:
        return link["href"].split("biblionumber=")[1]

    return None


async def fetch_detail(session, biblionumber):
    async with session.get(
        DETAIL_URL,
        params={"biblionumber": biblionumber},
        headers=HEADERS
    ) as r:
        soup = BeautifulSoup(await r.text(), "html.parser")

    def text(sel):
        el = soup.select_one(sel)
        return clean_text(el.get_text()) if el else None

    return {
        "title": text("h1.title"),
        "authors": [
            a.get_text(strip=True)
            for a in soup.select("span.results_summary.author span[property='name']")
        ],
        "isbn": text("span.results_summary.isbn span[property='isbn']"),
        "year": text("span.publisher_date"),
        "summary": text("p.marcnote-520"),
        "subjects": [
            s.get_text(strip=True)
            for s in soup.select("span.results_summary.subjects a.subject")
        ],
        "publisher": text("span.publisher_name"),
    }


async def process_row(session, sem, row, idx, total, saved, seen):
    async with sem:
        title = row["title"]
        isbn = row.get("isbn")

        key = book_key(isbn, title)
        if key in seen:
            return

        biblio = await search_opac(session, isbn, title)
        if not biblio:
            print(f"[{idx}/{total}] MISSING : {title[:50]}")
            return

        opac = await fetch_detail(session, biblio)
        print(f"[{idx}/{total}] FOUND : {title[:50]}")

        record = {
            "record_id": row["record_id"],
            "book_key": key,

            # local library metadata
            "accession_no": row.get("accession_no"),
            "class_no_book_no": row.get("class_no_book_no"),
            "pages": row.get("pages"),

            # authoritative OPAC fields (promoted)
            "title": opac.get("title"),
            "authors": opac.get("authors"),
            "isbn": opac.get("isbn"),
            "year": opac.get("year"),
            "subjects": opac.get("subjects"),
            "summary": opac.get("summary"),
            "publisher": opac.get("publisher"),
        }

        saved.append(record)
        seen.add(key)

        if len(saved) % SAVE_EVERY == 0:
            save_atomic(saved)
            print(f"Saved {len(saved)} records")


async def run_transformation():
    df = pd.read_csv(CLEAN_CSV)
    saved = load_existing()
    seen = {r["book_key"] for r in saved}

    print(f"Resuming OPAC enrichment")
    print(f"Already processed: {len(seen)}")
    print(f"Remaining: {len(df) - len(seen)}")

    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        tasks = [
            process_row(session, sem, row, i + 1, len(df), saved, seen)
            for i, row in df.iterrows()
            if book_key(row.get("isbn"), row["title"]) not in seen
        ]
        await asyncio.gather(*tasks)

    save_atomic(saved)
    print(f"Completed. Total enriched books: {len(saved)}")


def main():
    try:
        asyncio.run(run_transformation())
    except KeyboardInterrupt:
        save_atomic(load_existing())
        print("Interrupted safely. Progress saved.")

if __name__ == "__main__":
    main()
