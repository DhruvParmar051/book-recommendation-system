# 📚 Book Recommendation System  
### ETL Pipeline + Google Books Enrichment + FastAPI Service  
**A Complete Data Engineering Project**

---

## 1. Overview

This project implements a **full end-to-end data engineering pipeline** to prepare high-quality book data for analytics, semantic search, and recommendation systems.

The pipeline is designed to be:

- ✅ Deterministic  
- ✅ Resume-safe  
- ✅ Scalable  
- ✅ Self-documenting (every stage supports `--help`)  

### Implemented Stages

1. **Ingestion** – Load and standardize raw CSV files  
2. **Cleaning** – Normalize text, validate ISBNs, deduplicate  
3. **Transformation** – Enrich using Google Books API  
4. **Storage** – Persist enriched data to SQLite  
5. **Serving** – Expose data using FastAPI  

**Final Output**
- Cleaned & enriched SQLite database  
- REST API for querying books  

---

## 2. Project Structure

```
book-recommendation-system/
│
├── api/
│   └── main.py                  # FastAPI service
│
├── ingestion/
│   └── ingestion.py             # CSV ingestion stage
│
├── clean/
│   └── clean.py                 # Cleaning & deduplication
│
├── transformation/
│   └── transformation.py        # Google Books enrichment
│
├── storage/
│   └── db.py                    # JSON → SQLite loader
│
├── pipeline/
│   └── main.py                  # End-to-end pipeline runner
│
├── data/
│   ├── raw_data/
│   ├── ingested_data/
│   ├── clean_data/
│   ├── enriched_data/
│   └── storage_data/
│
├── requirements.txt
└── README.md
```

---

## 3. Installation

### 3.1 Clone the Repository

```
git clone https://github.com/YOUR-USERNAME/book-recommendation-system.git
cd book-recommendation-system
```

### 3.2 Install Dependencies

```
pip install -r requirements.txt
```

**Dependencies**

```
pandas
requests
fastapi
uvicorn
python-multipart
```

---

## 4. Pipeline Architecture

```
┌──────────────────────┐
│   Raw CSV Files      │
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────┐
│ INGESTION                  │
│ - Schema standardization   │
│ - Column unification       │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ CLEANING                   │
│ - Normalize text           │
│ - Validate ISBN            │
│ - Deduplicate records      │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ TRANSFORMATION              │
│ - Google Books enrichment  │
│ - Multithreaded + resume   │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ STORAGE                    │
│ - JSON → SQLite            │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ FASTAPI SERVICE            │
│ - Query books              │
│ - Serve recommendations    │
└────────────────────────────┘
```

---

## 5. Running the Full Pipeline

```
python pipeline/main.py
```

### What This Does

1. Runs **Ingestion**  
2. Runs **Cleaning**  
3. Runs **Transformation (Enrichment)**  
4. Runs **Storage**

### Final Output

```
data/storage_data/books.sqlite
```

### Execution Guarantees

- Stops immediately on failure  
- Fixed directory structure  
- Deterministic execution order  
- No partial or skipped stages  

---

## 6. FastAPI Service

### Start the API Server

```
uvicorn api.main:app --reload
```

### Access

- Swagger UI → http://localhost:8000/docs  
- Root Endpoint → http://localhost:8000/  

---

## 7. API Endpoints

### GET /

Returns a welcome message.

---

### GET /books?limit=10

Fetch recent books.

**Example Response**

```
[
  {
    "id": 1,
    "title": "Machine Learning",
    "author": "Tom Mitchell",
    "year": 1997
  }
]
```

---

### GET /books/{book_id}

Fetch a single book by ID.

---

### POST /sync

Run the pipeline in the background.

**Request Body**

```
{ "sample_size": 5 }
```

---

## 8. Pipeline Stage Details (Aligned with --help)

### 8.1 Ingestion (`ingestion/ingestion.py`)

**Purpose**
- Convert raw CSV files into a consistent schema.

**Input**
- `data/raw_data/*.csv`

**Operations**
- Rename raw headers using canonical mapping  
- Ensure all required columns exist  
- Normalize basic data types (ISBN, Year)  

**Output**
- `data/ingested_data/*.csv`

**Guarantees**
- Schema consistency  
- Safe re-runs  
- No data loss  

---

### 8.2 Cleaning (`clean/clean.py`)

**Purpose**
- Improve data quality and remove duplicates.

**Operations**
- Lowercase and trim text  
- Normalize ISBN (10/13-digit validation)  
- Drop rows without title  
- Deduplicate:
  - ISBN-based (preferred)
  - Title + author fallback  
- Year sanity checks (1500–2035)  
- Generate stable `record_id` (MD5 hash)

**Output**
- `data/clean_data/clean_books.csv`

---

### 8.3 Transformation (`transformation/transformation.py`)

**Purpose**
- Enrich books using Google Books API.

**Strategy**
1. Search by ISBN  
2. Fallback to title + author  

**Extracted Fields**
- Authors  
- Publisher  
- Published year  
- Categories (subjects)  
- Description  

**Execution Model**
- Multithreaded  
- Hard timeouts (freeze-proof)  
- Resume-safe  
- Atomic writes  

**Output**
- `data/enriched_data/enriched_books.json`

---

### 8.4 Storage (`storage/db.py`)

**Purpose**
- Persist enriched data into SQLite.

**Operations**
- Create database if missing  
- Create `books` table  
- Serialize lists as JSON strings  
- Insert using `INSERT OR IGNORE`

**Output**
- `data/storage_data/books.sqlite`

---

## 9. Data Statistics (Typical Run)

Collected via CLI logs:

- Total raw rows  
- Rows after cleaning  
- Duplicate removal count  
- Enriched records (`FOUND`)  
- Missing enrichment (`MISSING`)  
- Final database row count  

---

## 10. Data Dictionary

| Field | Description |
|------|------------|
| record_id | Stable MD5-based unique ID |
| book_key | Composite key (`isbn|title`) |
| status | FOUND / MISSING |
| accession_no | Library accession number |
| class_no_book_no | Classification number |
| pages | Page count |
| title | Cleaned book title |
| authors | JSON list of authors |
| isbn | Valid ISBN-10 / ISBN-13 |
| year | Publication year |
| subjects | JSON list of categories |
| summary | Book description |
| publisher | Publisher name |

---

## 11. Database Schema

```
Table: books

record_id        TEXT
book_key         TEXT UNIQUE
status           TEXT
accession_no     TEXT
class_no_book_no TEXT
pages            INTEGER
title            TEXT
authors          JSON TEXT
isbn             TEXT
year             TEXT
subjects         JSON TEXT
summary          TEXT
publisher        TEXT
```

---

## 12. Pipeline Flowchart

```
RAW CSV
  |
  v
ingestion.py
  |
  v
clean.py
  |
  v
transformation.py
  |
  v
db.py
  |
  v
SQLite Database
```

---

## 13. Future Enhancements

- Sentence Transformer embeddings  
- FAISS / Qdrant vector search  
- Semantic similarity recommendations  
- Google API caching  
- Airflow DAG  
- Dockerization  
- Unit & integration tests  
- Data quality dashboards  

---

## 14. Conclusion

This project delivers:

- ✅ Complete ETL pipeline  
- ✅ Resume-safe enrichment  
- ✅ Production-grade SQLite storage  
- ✅ Self-documenting CLI tools  
- ✅ FastAPI-based data serving  

You are now ready to build **semantic search** and **LLM-powered recommendation systems** on top of this pipeline.

---

🎉 **Enjoy your project — all the best!**
