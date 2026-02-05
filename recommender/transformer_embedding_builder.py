"""
Transformer Embedding Builder Script

This script builds semantic embeddings for books using a pretrained
transformer model. It constructs adaptive semantic text representations
that use book summaries when available and gracefully fall back to
structured metadata when summaries are missing.

This file represents the OFFLINE embedding stage of the
transformer-based recommendation system.
"""

import argparse
import pickle
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ================== EMBEDDING CONFIG ==================

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

EMBED_COLUMNS = [
    "summary",
    "subjects",
    "title",
    "publisher"
    "class_no_book_no",
]

# ================== TEXT CONSTRUCTION ==================

def build_semantic_text(row: pd.Series) -> str:
    """
    Build adaptive semantic text for a book.

    Priority:
    1. Summary (if present)
    2. Title
    3. Subjects
    4. Classification
    5. Publisher
    """
    parts = []

    for col in EMBED_COLUMNS:
        val = row.get(col)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())

    return " ".join(parts)

# ================== EMBEDDING LOGIC ==================

def build_embeddings(
    input_csv: Path,
    output_dir: Path,
    model_name: str
) -> None:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)

    # Build semantic text per book
    df["semantic_text"] = df.apply(build_semantic_text, axis=1)

    print("Loading transformer model...")
    model = SentenceTransformer(model_name)

    print("Encoding book texts...")
    embeddings = model.encode(
        df["semantic_text"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=True
    )

    # Persist artifacts
    with open(output_dir / "book_embeddings.pkl", "wb") as f:
        pickle.dump(embeddings, f)
        

    df[["record_id"]].to_csv(
        output_dir / "embedding_index.csv",
        index=False
    )

    print("Embedding build complete")
    print(f"Embeddings saved to: {output_dir}")
    print(f"Total books encoded: {len(df)}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""TRANSFORMER EMBEDDING BUILDER

PURPOSE
-------
Build semantic embeddings for books using a pretrained
transformer model.

INPUT
-----
- Recommender-ready feature CSV
- May contain missing summaries

PROCESSING
----------
1. Construct adaptive semantic text per book
2. Use summaries when available
3. Fall back to structured metadata otherwise
4. Encode texts using a sentence transformer
5. Persist embeddings for fast reuse

OUTPUT
------
- Serialized embedding matrix (pickle)
- Index mapping record_id → embedding row

NOT INCLUDED
------------
- No recommendation logic
- No similarity search
- No online inference
- No model training
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    parser.add_argument(
        "--input-csv",
        type=Path,
        default=PROJECT_ROOT / "data/processed_data/books_features.csv",
        help="Input feature CSV (default: data/processed_data/books_features.csv)"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "storage/embeddings",
        help="Directory to store embeddings (default: storage/embeddings)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Transformer model name (default: {DEFAULT_MODEL})"
    )

    args = parser.parse_args()

    build_embeddings(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        model_name=args.model
    )

if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================
