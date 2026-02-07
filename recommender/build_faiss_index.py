"""
FAISS Index Builder Script (CORRECT + PRODUCTION SAFE)

This script builds an Approximate Nearest Neighbor (ANN) index
using FAISS from precomputed transformer embeddings.

CRITICAL GUARANTEE
------------------
- Preserves row order
- Stores record_id mapping
- Compatible with low-RAM inference
- One-time offline job

OUTPUT FILES
------------
storage/embeddings/
 ├── faiss.index
 └── index_metadata.pkl  ✅ contains record_ids
"""

import argparse
import pickle
import faiss
import numpy as np
import pandas as pd
from pathlib import Path

# ================== INDEX CONFIG ==================

FAISS_METRIC = "cosine"

# ================== INDEX LOGIC ==================

def build_faiss_index(
    embedding_dir: Path,
    feature_csv: Path
) -> None:
    embeddings_path = embedding_dir / "book_embeddings.pkl"

    if not embeddings_path.exists():
        raise FileNotFoundError(f"Embeddings not found: {embeddings_path}")

    if not feature_csv.exists():
        raise FileNotFoundError(f"Feature CSV not found: {feature_csv}")

    # ------------------------------
    # Load embeddings
    # ------------------------------
    with open(embeddings_path, "rb") as f:
        embeddings = pickle.load(f)

    embeddings = np.asarray(embeddings).astype("float32")
    dim = embeddings.shape[1]

    # ------------------------------
    # Load record_id mapping
    # ------------------------------
    df = pd.read_csv(feature_csv)

    if "record_id" not in df.columns:
        raise ValueError("feature CSV must contain 'record_id' column")

    record_ids = df["record_id"].tolist()

    if len(record_ids) != len(embeddings):
        raise ValueError(
            f"Mismatch: {len(record_ids)} record_ids vs {len(embeddings)} embeddings"
        )

    print(f"Building FAISS index (dim={dim}, size={len(embeddings)})")

    # ------------------------------
    # Build FAISS index (cosine)
    # ------------------------------
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(embedding_dir / "faiss.index"))

    # ------------------------------
    # SAVE METADATA (THIS FIXES YOUR BUG)
    # ------------------------------
    with open(embedding_dir / "index_metadata.pkl", "wb") as f:
        pickle.dump(
            {
                "metric": FAISS_METRIC,
                "dimension": dim,
                "count": len(embeddings),
                "record_ids": record_ids,   # 🔑 REQUIRED BY RECOMMENDER
            },
            f
        )

    print("✅ FAISS index successfully built")
    print(f"📁 Index saved to: {embedding_dir / 'faiss.index'}")
    print(f"📁 Metadata saved to: {embedding_dir / 'index_metadata.pkl'}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description="""
FAISS INDEX BUILDER (LOW-RAM SAFE)

PURPOSE
-------
Build ANN index for semantic retrieval.

INPUT
-----
- Precomputed embeddings
- Feature CSV with record_id

PROCESS
-------
1. Load embeddings
2. Normalize vectors
3. Build FAISS index
4. Store record_id mapping

OUTPUT
------
- faiss.index
- index_metadata.pkl (record_ids included)
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    parser.add_argument(
        "--embedding-dir",
        type=Path,
        default=PROJECT_ROOT / "storage/embeddings",
        help="Directory containing book_embeddings.pkl"
    )

    parser.add_argument(
        "--feature-csv",
        type=Path,
        default=PROJECT_ROOT / "data/processed_data/books_features.csv",
        help="CSV containing record_id column"
    )

    args = parser.parse_args()

    build_faiss_index(
        embedding_dir=args.embedding_dir,
        feature_csv=args.feature_csv
    )

if __name__ == "__main__":
    main()

# ================== END OF FILE ==================
