# Book Recommendation System  
### ETL Pipeline + Google Books Enrichment + FastAPI Service  
A complete Data Engineering Project

---

# 1. Overview

This project builds a full **data engineering + data serving pipeline** to prepare high-quality book data for a semantic book-recommendation system.

It implements all 4 required steps from the project specification:

1. **Ingestion** – Load raw CSV files  
2. **Cleaning** – Normalize & deduplicate  
3. **Transformation** – Enrich using Google Books API  
4. **Storage** – Save enriched results to SQLite  
5. **Serving** – Provide an API using FastAPI

The final output is a complete, cleaned, enriched books database and an API to access it.

---

# 2. Project Structure

```
book-recommendation-system/
│
├── api/
│   └── main.py
│
├── ingestion/
│   └── ingestion.py
│
├── clean/
│   └── clean.py
│
├── transformation/
│   └── transformation.py
│
├── storage/
│   └── db.py
│
├── pipeline/
│   └── main.py
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

# 3. Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR-USERNAME/book-recommendation-system.git
cd book-recommendation-system
```

### 2️. Install dependencies
```
pip install -r requirements.txt
```

Requirements:
```
pandas
requests
fastapi
uvicorn
python-multipart
```

---

# 3. Architecture Diagram

```
                   ┌──────────────────┐
                   │  Raw CSV Files   │
                   └────────┬─────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │  INGESTION (CSV → STD) │
               └────────┬───────────────┘
                        │
                        ▼
          ┌────────────────────────────┐
          │   CLEANING (Normalize +    │
          │     Deduplicate + ISBN)    │
          └──────────┬─────────────────┘
                     │
                     ▼
      ┌──────────────────────────────────┐
      │ TRANSFORMATION (Google Books API │
      │     Enrichment: authors, desc)   │
      └──────────────┬──────────────────┘
                     │
                     ▼
     ┌──────────────────────────────────┐
     │ STORAGE (JSON → SQLite Database) │
     └─────────────────┬────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  FASTAPI SERVICE    │
            │  (books, details)   │
            └─────────────────────┘
```

---

# 4. Running the FULL Pipeline (All Steps)

Run all ETL stages:

```bash
python pipeline/main.py
```

This runs:

1. INGESTION  
2. CLEANING  
3. TRANSFORMATION  
4. STORAGE  

Final DB created at:

```
data/storage_data/books.sqlite
```

---

# 5. Running the API Server

Start FastAPI:

```bash
uvicorn api.main:app --reload
```

Visit:

- Swagger UI → http://localhost:8000/docs  
- Root → http://localhost:8000/

---

# 6. API Documentation

### **GET /**  
Welcome message

---

### **GET /books?limit=10**  
Get recent books.

**Response example:**
```json
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

### **GET /books/{book_id}**  
Fetch a specific book.

---

### **POST /sync**  
Run pipeline in background.

**Body:**  
```json
{ "sample_size": 5 }
```

---

# 7. Step-by-Step Code Explanation

---

## 7.1 INGESTION (`ingestion/ingestion.py`)

 Reads all CSV files from `data/raw_data/`  
 Standardizes headers using `COLUMN_MAPPING`  
 Fixes year & isbn basic types  
 Saves standardized data into `data/ingested_data/`

---

## 7.2 CLEANING (`clean/clean.py`)

 Converts text → lowercase  
 Removes duplicate ISBNs  
 Deduplicates books without ISBN using (title + author)  
 Normalizes ISBN to (10/13-digit valid)  
 Fixes incorrect years (<1500 or >2035 → NULL)  
 Builds a stable `record_id` using MD5 hash  
 Outputs `clean_books.csv`

---

## 7.3 TRANSFORMATION (`transformation/transformation.py`)

 Loads clean CSV  
 Multithreaded Google Books API calls  
 Tries:

1. Search by ISBN  
2. Search by title + author  

 Extracts:

- authors  
- publisher  
- published year  
- categories (subjects)  
- description  

 Saves enriched JSON into `enriched_books.json`

---

## 7.4 STORAGE (`storage/db.py`)

 Reads enriched JSON  
 Creates SQLite database  
 Creates `books` table  
 Inserts all enriched rows into the database  
 Saves DB to:

```
data/storage_data/books.sqlite
```

---

# 8. Data Dictionary

| Field | Description |
|-------|-------------|
| record_id | MD5 hash (stable unique ID) |
| book_key | Unique composite key (isbn|title) |
| status | FOUND / MISSING |
| accession_no | Library accession number |
| class_no_book_no | Classification number |
| pages | Page count |
| title | Final cleaned title |
| authors | List of authors from Google Books |
| isbn | Valid ISBN-10 or ISBN-13 |
| year | Publication year |
| subjects | Category list |
| summary | Description |
| publisher | Publisher name |

---

# 9. Database ER Diagram

```
┌──────────────────────────────────────────────────┐
│                     books                        │
├──────────────────────────────────────────────────┤
│ record_id (TEXT)                                 │
│ book_key (TEXT)  UNIQUE                          │
│ status (TEXT)                                    │
│ accession_no (TEXT)                              │
│ class_no_book_no (TEXT)                          │
│ pages (INTEGER)                                  │
│ title (TEXT)                                     │
│ authors (JSON TEXT)                              │
│ isbn (TEXT)                                      │
│ year (TEXT)                                      │
│ subjects (JSON TEXT)                             │
│ summary (TEXT)                                   │
│ publisher (TEXT)                                 │
└──────────────────────────────────────────────────┘
```

---

# 10. Pipeline Flowchart

```
          +---------------------+
          |   RAW CSV FILES     |
          +---------------------+
                    |
                    v
     +--------------------------------+
     |  ingestion.py                  |
     |  - rename columns              |
     |  - unify schema                |
     +--------------------------------+
                    |
                    v
     +--------------------------------+
     |   clean.py                     |
     |  - normalize text              |
     |  - fix isbn                    |
     |  - remove duplicates           |
     +--------------------------------+
                    |
                    v
     +--------------------------------+
     | transformation.py              |
     | - Google Books API lookup      |
     | - extract authors/summary      |
     +--------------------------------+
                    |
                    v
     +--------------------------------+
     |       db.py                    |
     |   JSON → SQLite database       |
     +--------------------------------+
```

---

# 11. Future Enhancements

- Add embeddings using Sentence Transformers  
- Add FAISS or Qdrant vector search  
- Recommend similar books  
- Add caching for Google API  
- Convert pipeline into Airflow DAG  
- Add Dockerfile  
- Add unit tests for each pipeline stage  

---

# 12. Conclusion

This project provides:

 A complete ETL pipeline  
 Property-normalized dataset  
 Book enrichment using Google APIs  
 SQLite database output  
 FastAPI service to serve books  

You're now ready to build **semantic search** and **LLM-powered recommendation systems** on top of this.

---

#  Enjoy your project , All the best!

