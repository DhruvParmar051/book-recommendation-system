import json
import sqlite3
from pathlib import Path

# ================== CONFIG ==================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_JSON = DATA_DIR / "enriched_data" / "enriched_books.json"
OUTPUT_DB = DATA_DIR / "storage_data" / "books.sqlite"

TABLE_NAME = "books"

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    records = json.load(f)

if not records:
    raise ValueError("JSON file is empty")

conn = sqlite3.connect(OUTPUT_DB)
cursor = conn.cursor()

cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    record_id INTEGER,
    book_key TEXT UNIQUE,
    status TEXT,
    accession_no TEXT,
    class_no_book_no TEXT,
    pages INTEGER,
    title TEXT,
    authors TEXT,
    isbn TEXT,
    year TEXT,
    subjects TEXT,
    summary TEXT,
    publisher TEXT
);
""")

insert_sql = f"""
INSERT OR IGNORE INTO {TABLE_NAME} (
    record_id, book_key, status,
    accession_no, class_no_book_no, pages,
    title, authors, isbn, year,
    subjects, summary, publisher
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

rows = []

for r in records:
    rows.append((
        r.get("record_id"),
        r.get("book_key"),
        r.get("status"),
        r.get("accession_no"),
        r.get("class_no_book_no"),
        r.get("pages"),
        r.get("title"),
        json.dumps(r.get("authors"), ensure_ascii=False),
        r.get("isbn"),
        r.get("year"),
        json.dumps(r.get("subjects"), ensure_ascii=False),
        r.get("summary"),
        r.get("publisher"),
    ))

cursor.executemany(insert_sql, rows)
conn.commit()
conn.close()

print(f"JSON → SQLite conversion complete")
print(f"Database saved at: {OUTPUT_DB}")
print(f"Records inserted: {len(rows)}")
