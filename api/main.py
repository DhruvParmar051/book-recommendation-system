"""
FastAPI Book Recommendation Service (Render Safe)
"""

import sys
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel

from recommender.advanced_transformer_recommender import AdvancedTransformerRecommender

# ======================================================
# PROJECT SETUP
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# ======================================================
# DATA PATHS
# ======================================================

DATA_DIR = PROJECT_ROOT / "data"
FEATURES_CSV = DATA_DIR / "processed_data" / "books_features.csv"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DB_PATH = DATA_DIR / "storage_data" / "books.sqlite"

# ======================================================
# DATABASE
# ======================================================

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ======================================================
# DATABASE MODEL
# ======================================================

class Book(Base):
    __tablename__ = "books"

    record_id = Column(String, primary_key=True)
    title = Column(String)
    authors = Column(String)
    publisher = Column(String)
    year = Column(String)
    subjects = Column(String)
    summary = Column(Text)
    pages = Column(String)
    isbn = Column(String)

# ======================================================
# DEPENDENCY
# ======================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======================================================
# HELPERS
# ======================================================

def clean_value(val):
    if val is None:
        return None
    val = str(val).strip()
    return val if val and val.lower() not in {"null", "none"} else None

def format_list(val):
    if not val:
        return None
    if val.startswith("[") and val.endswith("]"):
        try:
            return ", ".join(eval(val))
        except Exception:
            pass
    return val

# ======================================================
# SCHEMAS
# ======================================================

class RecommendationRequest(BaseModel):
    query: str
    top_k: int = 5

# ======================================================
# FASTAPI APP
# ======================================================

app = FastAPI(
    title="Book Recommendation API",
    version="1.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# RECOMMENDER (LAZY LOAD)
# ======================================================

recommender = None

@app.on_event("startup")
def load_recommender():
    """
    Runs AFTER the server starts listening on a port.
    NEVER crash here — fail gracefully.
    """
    global recommender

    try:
        print("🚀 Startup checks...")

        if not FEATURES_CSV.exists():
            raise RuntimeError(f"Missing {FEATURES_CSV}")

        if not (EMBEDDINGS_DIR / "faiss.index").exists():
            raise RuntimeError("Missing faiss.index")

        if not (EMBEDDINGS_DIR / "index_metadata.pkl").exists():
            raise RuntimeError("Missing index_metadata.pkl")

        if not DB_PATH.exists():
            raise RuntimeError(f"Missing {DB_PATH}")

        recommender = AdvancedTransformerRecommender(
            data_csv=FEATURES_CSV,
            embedding_dir=EMBEDDINGS_DIR
        )

        print("✅ Recommender loaded successfully")

    except Exception as e:
        recommender = None
        print(f"❌ Startup error: {e}")

# ======================================================
# HEALTH CHECK
# ======================================================

@app.get("/")
def health():
    return {
        "status": "ok",
        "recommender_loaded": recommender is not None
    }

# ======================================================
# BROWSE BOOKS
# ======================================================

@app.get("/books/")
def browse_books(
    skip: int = 0,
    limit: int = 10,
    search_field: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Book)

    if search_field and query:
        column = {
            "title": Book.title,
            "authors": Book.authors,
            "publisher": Book.publisher
        }.get(search_field)

        if not column:
            raise HTTPException(400, "Invalid search_field")

        q = q.filter(func.lower(column).like(f"%{query.lower()}%"))

    total = q.count()
    books = q.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "title": clean_value(b.title),
                "authors": format_list(clean_value(b.authors)),
                "publisher": clean_value(b.publisher),
                "year": clean_value(b.year),
                "subjects": format_list(clean_value(b.subjects)),
                "summary": clean_value(b.summary),
                "pages": clean_value(b.pages),
                "isbn": clean_value(b.isbn),
            }
            for b in books
        ]
    }

# ======================================================
# RECOMMENDATION
# ======================================================
@app.post("/recommend")
def recommend_books(
    req: RecommendationRequest,
    db: Session = Depends(get_db)
):
    if recommender is None:
        raise HTTPException(503, "Recommendation engine not available")

    results = recommender.recommend(req.query, req.top_k)

    if not results:
        return []

    record_ids = [r["record_id"] for r in results]
    score_map = {r["record_id"]: r["final_score"] for r in results}

    books = (
        db.query(Book)
        .filter(Book.record_id.in_(record_ids))
        .all()
    )

    books.sort(
        key=lambda b: score_map.get(b.record_id, 0.0),
        reverse=True
    )

    return [
        {
            "title": clean_value(b.title),
            "authors": format_list(clean_value(b.authors)),
            "publisher": clean_value(b.publisher),
            "year": clean_value(b.year),
            "subjects": format_list(clean_value(b.subjects)),
            "summary": clean_value(b.summary),
            "pages": clean_value(b.pages),
            "isbn": clean_value(b.isbn),
            "score": score_map[b.record_id],
        }
        for b in books
    ]
