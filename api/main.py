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
from api.utils.hf_loader import load_books_dataset 

# ======================================================
# PROJECT SETUP
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# ---------- DATA LOCATIONS (Render + Local safe) ----------
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

HF_CACHE_DIR = DATA_DIR / "hf_cache"
HF_CACHE_DIR.mkdir(exist_ok=True)

FEATURES_CSV = DATA_DIR / "books_features.csv"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
EMBEDDINGS_DIR.mkdir(exist_ok=True)

# ---------- DATABASE ----------
DB_PATH = DATA_DIR / "storage_data" / "books.sqlite"

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

app = FastAPI(title="Book Recommendation API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# LOAD RECOMMENDER (HF-FIRST, FAIL-SAFE)
# ======================================================

recommender = None

HF_DATASET_NAME = "DhruvParmar051/book-recommender-assets"

@app.on_event("startup")
def load_recommender():
    global recommender

    try:
        # --------- STEP 1: Ensure features CSV exists ----------
        if not FEATURES_CSV.exists():
            print("⬇️ Loading dataset from Hugging Face...")
            df = load_books_dataset(
                dataset_name=HF_DATASET_NAME,
                cache_dir=HF_CACHE_DIR
            )

            # Ensure record_id exists
            if "record_id" not in df.columns:
                df["record_id"] = df.index.astype(str)

            df = df.fillna("")
            df.to_csv(FEATURES_CSV, index=False)
            print("✅ books_features.csv created")

        # --------- STEP 2: Load recommender ----------
        recommender = AdvancedTransformerRecommender(
            data_csv=FEATURES_CSV,
            embedding_dir=EMBEDDINGS_DIR
        )

        print("🚀 Recommender loaded successfully")

    except Exception as e:
        recommender = None
        print(f"⚠️ Recommender disabled: {e}")

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

    return {"total": total, "items": items}

# ======================================================
# RECOMMENDATION ENDPOINT
# ======================================================

@app.post("/recommend")
def recommend_books(req: RecommendationRequest, db: Session = Depends(get_db)):
    if recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation engine warming up"
        )

    df = recommender.recommend(req.query, req.top_k)

    if df.empty:
        return []

    record_ids = df["record_id"].tolist()
    score_map = dict(zip(df["record_id"], df["final_score"]))

    books = (
        db.query(Book)
        .filter(Book.record_id.in_(record_ids))
        .all()
    )

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
