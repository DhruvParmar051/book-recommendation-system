"""
FastAPI Book Recommendation Service
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from recommender.advanced_transformer_recommender import AdvancedTransformerRecommender
from utils.kaggle_loader import download_kaggle_dataset

# ======================================================
# PROJECT SETUP
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "storage_data" / "books.sqlite"

import os

DATA_CSV = os.getenv("BOOKS_FEATURES_CSV")
EMBED_DIR = os.getenv("EMBEDDINGS_DIR")

if not DATA_CSV or not EMBED_DIR:
    raise RuntimeError("Missing ML data paths")


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
    if isinstance(val, float) and val != val:
        return None
    val = str(val).strip()
    return val if val.lower() not in {"", "null", "none"} else None

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

app = FastAPI(title="Book Recommendation API", version="1.2.0")


recommender = None

@app.on_event("startup")
def load_recommender():
    global recommender

    download_kaggle_dataset()

    recommender = AdvancedTransformerRecommender(
    data_csv=Path(DATA_CSV),
    embedding_dir=Path(EMBED_DIR)
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# BROWSE + SEARCH BOOKS
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
        if search_field not in {"title", "authors", "publisher"}:
            raise HTTPException(status_code=400, detail="Invalid search_field")

        column = {
            "title": Book.title,
            "authors": Book.authors,
            "publisher": Book.publisher
        }[search_field]

        q = q.filter(
            column.isnot(None),
            func.lower(column).like(f"%{query.lower()}%")
        )

    total = q.count()
    books = q.offset(skip).limit(limit).all()

    items = []
    for b in books:
        item = {
            "title": clean_value(b.title),
            "authors": format_list(clean_value(b.authors)),
            "publisher": clean_value(b.publisher),
            "year": clean_value(b.year),
            "subjects": format_list(clean_value(b.subjects)),
            "summary": clean_value(b.summary),
            "pages": clean_value(b.pages),
            "isbn": clean_value(b.isbn),
        }
        item = {k: v for k, v in item.items() if v is not None}
        items.append(item)

    return {
        "total": total,
        "items": items
    }


@app.post("/recommend")
def recommend_books(req: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Semantic book recommendation endpoint.
    """
    if recommender is None:
        raise HTTPException(status_code=503, detail="Recommender not loaded")

    # Get ranked results from transformer
    df = recommender.recommend(req.query, req.top_k)

    if df.empty:
        return []

    record_ids = df["record_id"].tolist()
    score_map = dict(zip(df["record_id"], df["final_score"]))

    # Fetch full book data from DB
    books = (
        db.query(Book)
        .filter(Book.record_id.in_(record_ids))
        .all()
    )

    # Preserve ranking order
    books.sort(key=lambda b: score_map[b.record_id], reverse=True)

    results = []
    for b in books:
        item = {
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
        item = {k: v for k, v in item.items() if v is not None}
        results.append(item)

    return results
