"""
JSON to SQLite Loader Script

This script loads enriched book records from a JSON file
and stores them into a SQLite database. It represents the
final storage stage of the data pipeline.
"""

import argparse
import json
import sqlite3
from pathlib import Path

TABLE_NAME = "books"

# ================== MAIN LOGIC ==================

def run_loader(input_json: Path, output_db: Path):
    if not input_json.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_json}")

    output_db.parent.mkdir(parents=True, exist_ok=True)

    with open(input_json, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        raise ValueError("JSON file is empty")

    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        record_id TEXT,
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

    print("JSON → SQLite conversion complete")
    print(f"Database saved at: {output_db}")
    print(f"Records inserted: {len(rows)}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""JSON TO SQLITE LOADER SCRIPT

PURPOSE
-------
Loads enriched book records from a JSON file into a SQLite database.
This is the final storage stage of the data pipeline.

INPUT
-----
- Enriched JSON file

STORAGE PROCESS
---------------
1. Load enriched book records from JSON
2. Create SQLite database if it does not exist
3. Create books table with fixed schema
4. Insert records safely using INSERT OR IGNORE
5. Serialize list fields (authors, subjects) as JSON strings

OUTPUT
------
- SQLite database file

DATABASE DETAILS
----------------
- Table name: books
- Unique constraint on book_key
- Duplicate records are ignored safely

NOT INCLUDED
------------
- No schema migration
- No updates to existing records
- No indexing
- No external database usage
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input-json",
        type=Path,
        default=Path("data/enriched_data/enriched_books.json"),
        help="Path to enriched JSON file (default: data/enriched_data/enriched_books.json)"
    )

    parser.add_argument(
        "--output-db",
        type=Path,
        default=Path("data/storage_data/books.sqlite"),
        help="Path to output SQLite database (default: data/storage_data/books.sqlite)"
    )

    args = parser.parse_args()

    run_loader(args.input_json, args.output_db)


if __name__ == "__main__":
    main()
# ================== END OF SCRIPT ==================