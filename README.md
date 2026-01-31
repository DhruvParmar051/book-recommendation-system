# 📚 Book Recommendation System  
### End-to-End ETL Pipeline + Google Books Enrichment + FastAPI Service  
**A Complete Data Engineering Project**

---

## 1. Introduction & Motivation

Modern recommendation systems rely on **clean, structured, and enriched data**.  
Raw library or OPAC datasets are often:

- Inconsistent in schema
- Noisy and duplicated
- Missing semantic metadata (authors, categories, descriptions)

This project addresses those challenges by building a **production-style data pipeline**
that transforms raw CSV book records into a **queryable, enriched database**, and exposes
the data through a **REST API** for downstream applications such as:

- Book recommendation systems
- Semantic search
- Analytics dashboards
- LLM-based applications

The project follows **real-world data engineering principles**:
- Clear separation of pipeline stages
- Deterministic and resume-safe processing
- CLI-driven configuration
- Database-backed persistence
- API-based data access

---

## 2. High-Level Capabilities

This system provides:

- 📥 Robust ingestion of raw CSV files
- 🧹 Data cleaning, normalization, and deduplication
- 🌐 External enrichment via Google Books API
- 💾 Persistent storage using SQLite
- 🚀 FastAPI service for browsing and searching books
- 🧪 Fully self-documenting CLI (`--help` on every stage)

---

## 3. Project Structure & Responsibilities

Each folder has **one clear responsibility**, mirroring how production pipelines are organized.

```
book-recommendation-system/
│
├── api/
│   └── main.py
├── ingestion/
│   └── ingestion.py
├── clean/
│   └── clean.py
├── transformation/
│   └── transformation.py
├── storage/
│   └── db.py
├── pipeline/
│   └── main.py
├── data/
│   ├── raw_data/
│   ├── ingested_data/
│   ├── clean_data/
│   ├── enriched_data/
│   └── storage_data/
└── README.md
```

This structure ensures:
- Clear data lineage
- Easy debugging
- Independent execution of each stage

---

## 4. 🔽 Pipeline Architecture (End-to-End Flow)

The pipeline is **linear, deterministic, and restartable**.

```
┌──────────────────────┐
│   Raw CSV Files      │
│  (Untrusted Input)   │
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────┐
│ INGESTION                  │
│ - Standardize schema       │
│ - Ensure required columns  │
│ - Minimal type fixes       │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ CLEANING                   │
│ - Normalize text           │
│ - Validate ISBNs           │
│ - Deduplicate records      │
│ - Generate stable IDs      │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ TRANSFORMATION             │
│ - Google Books API         │
│ - Multithreaded enrichment │
│ - Resume-safe execution    │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ STORAGE                    │
│ - JSON → SQLite            │
│ - Duplicate-safe inserts   │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ FASTAPI SERVICE            │
│ - Browse books             │
│ - Search & lookup          │
│ - Trigger pipeline         │
└────────────────────────────┘
```

---

## 5. Running the Complete Pipeline

To execute **all ETL stages in order**, run:

```
python pipeline/main.py
```

### What Happens Internally

1. Ingests raw CSV files  
2. Cleans and deduplicates records  
3. Enriches books using Google Books API  
4. Stores final results in SQLite  

### Final Artifact

```
data/storage_data/books.sqlite
```

This database becomes the **single source of truth** for the API.

---

## 6. Detailed Stage Explanations

---

### 6.1 Ingestion Stage

**Goal:**  
Convert raw, inconsistent CSV files into a **canonical schema**.

**Key Design Choices**
- No cleaning or deduplication (by design)
- Schema-first approach
- Fail-safe handling of missing columns

**Why this matters:**  
Keeps ingestion lightweight and repeatable, deferring complex logic to later stages.

**Default Run**

```
python ingestion/ingestion.py
```

**Custom Input / Output**

```
python ingestion/ingestion.py \
  --input-dir my_raw_csvs \
  --output-dir my_ingested_csvs
```

---

### 6.2 Cleaning Stage

**Goal:**  
Improve data quality and remove redundancy.

**Operations**
- Normalize text (lowercase, trim, whitespace fix)
- Validate ISBNs (10/13-digit)
- Drop records without titles
- Deduplicate:
  - ISBN-based (preferred)
  - Title + Author fallback
- Generate stable `record_id` using hashing

**Why this matters:**  
Downstream enrichment and storage rely on **high-quality, unique records**.

**Default Run**

```
python clean/clean.py
```

**Custom Input / Output**

```
python clean/clean.py \
  --input-dir data/ingested_data \
  --output-file output/clean_books.csv
```

---

### 6.3 Transformation (Enrichment) Stage

**Goal:**  
Add semantic metadata using Google Books API.

**Enrichment Strategy**
1. Search by ISBN (highest precision)
2. Fallback to title + author search

**Reliability Features**
- Multithreading with controlled concurrency
- Hard API timeouts
- Incremental atomic saves
- Resume-safe after interruption

**Why this matters:**  
External APIs are unreliable—this design prevents data loss and freezes.

**Default Run**

```
python transformation/transformation.py
```

**Custom Input / Output**

```
python transformation/transformation.py \
  --input-csv clean.csv \
  --output-json enriched.json
```

---

### 6.4 Storage Stage

**Goal:**  
Persist enriched records in a **query-efficient format**.

**Design Choices**
- SQLite (simple, portable, zero-config)
- Fixed schema
- `INSERT OR IGNORE` to prevent duplicates
- JSON serialization for list fields

**Why SQLite?**
- Ideal for small–medium datasets
- Easy integration with FastAPI
- No external service required

**Default Run**

```
python storage/db.py
```

**Custom Input / Output**

```
python storage/db.py \
  --input-json enriched.json \
  --output-db books.sqlite
```

---

## 7. FastAPI Service

The FastAPI layer provides **read-only access** to the final dataset.

### Key Endpoints

- `GET /books/` – Paginated book listing  
- `GET /books/isbn/{isbn}` – ISBN lookup  
- `GET /search/?q=term` – Full-text search  
- `POST /sync/` – Trigger pipeline in background  

### Start API Server

```
uvicorn api.main:app --reload
```

### Available Endpoints

- `GET /books/`
- `GET /books/isbn/{isbn}`
- `GET /search/?q=term`
- `POST /sync/` – trigger pipeline in background

Swagger UI:
http://localhost:8000/docs

---

## 8. Data Dictionary (Core Fields)

| Field | Description |
|------|------------|
| record_id | Stable hashed identifier |
| book_key | Unique composite key |
| status | FOUND / MISSING |
| title | Normalized title |
| authors | Author list (JSON) |
| isbn | Valid ISBN |
| year | Publication year |
| subjects | Category list |
| summary | Description |
| publisher | Publisher name |

---

## 9. Design Philosophy

This project emphasizes:

- **Separation of concerns**
- **Reproducibility**
- **Operational safety**
- **Explainability**
- **Real-world engineering patterns**

It is intentionally designed to be:
- Extendable to Airflow / Prefect
- Ready for vector embeddings
- Suitable for ML & LLM pipelines

---

## 10. Future Enhancements

- Sentence Transformer embeddings
- Vector search (FAISS / Qdrant)
- Recommendation engine
- API authentication
- Caching & rate limiting
- Docker & CI/CD
- Data quality dashboards

---

## 11. Conclusion

This project demonstrates a **complete, production-style data pipeline**:

- ✅ Modular ETL design  
- ✅ Dynamic, CLI-driven execution  
- ✅ Resume-safe enrichment  
- ✅ Persistent storage  
- ✅ API-based data access  

It forms a strong foundation for **semantic search and recommendation systems**.

---

🎉 **Great work building a full data engineering system — all the best!**
