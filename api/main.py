from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, or_
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os
import sys
import subprocess
import threading

# ======================================================
# DATABASE CONFIG (MATCHES YOUR PROJECT STRUCTURE)
# ======================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///../data/storage_data/books.sqlite"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ======================================================
# DATABASE MODEL (MATCHES SQLITE TABLE)
# ======================================================

class Book(Base):
    __tablename__ = "books"

    record_id = Column(Integer, primary_key=True, index=True)
    book_key = Column(String, unique=True, index=True)
    status = Column(String)

    accession_no = Column(String, nullable=True)
    class_no_book_no = Column(String, nullable=True)
    pages = Column(Integer, nullable=True)

    title = Column(String, index=True)
    authors = Column(String, nullable=True)     # JSON string
    isbn = Column(String, index=True)
    year = Column(String, nullable=True)

    subjects = Column(String, nullable=True)    # JSON string
    summary = Column(Text, nullable=True)
    publisher = Column(String, nullable=True)

# IMPORTANT: Do NOT recreate table here (already exists)
# Base.metadata.create_all(bind=engine) ❌

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
# SCHEMAS
# ======================================================

class BookBase(BaseModel):
    record_id: str                     # ✅ STRING
    book_key: str
    status: str

    accession_no: Optional[str]
    class_no_book_no: Optional[str]
    pages: Optional[str]               # ✅ STRING

    title: Optional[str]
    authors: Optional[str]
    isbn: Optional[str]
    year: Optional[str]

    subjects: Optional[str]
    summary: Optional[str]
    publisher: Optional[str]


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

# ======================================================
# FASTAPI APP
# ======================================================

app = FastAPI(
    title="Book Recommendation API",
    description="API for searching books enriched using Google Books",
    version="1.0.0"
)

# ======================================================
# CORS
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# ROUTES
# ======================================================

@app.get("/books/", response_model=List[BookResponse])
def get_books(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return db.query(Book).offset(skip).limit(limit).all()


@app.get("/books/isbn/{isbn}", response_model=BookResponse)
def get_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.get("/search/", response_model=List[BookResponse])
def search_books(
    q: str = Query(..., min_length=3),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    pattern = f"%{q}%"
    return db.query(Book).filter(
        or_(
            Book.title.ilike(pattern),
            Book.authors.ilike(pattern),
            Book.isbn == q
        )
    ).limit(limit).all()

# ======================================================
# PIPELINE TRIGGER (OPTIONAL)
# ======================================================

pipeline_lock = threading.Lock()

@app.post("/sync/")
def trigger_pipeline():
    """
    Runs main.py (pipeline) in background
    """
    def run_pipeline():
        if not pipeline_lock.acquire(blocking=False):
            return
        try:
            subprocess.run(
                [sys.executable, "../main.py"],
                cwd=os.getcwd()
            )
        finally:
            pipeline_lock.release()

    threading.Thread(target=run_pipeline, daemon=True).start()

    return {
        "status": "started",
        "message": "Pipeline triggered in background"
    }

# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
