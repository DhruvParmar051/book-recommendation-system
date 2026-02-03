"""
FAISS Index Builder Script

This script builds an Approximate Nearest Neighbor (ANN) index
using FAISS from precomputed transformer embeddings.

This file represents the OFFLINE INDEXING stage of the
advanced transformer-based recommendation system.
"""

import argparse
import pickle
import faiss
import numpy as np
from pathlib import Path

# ================== INDEX CONFIG ==================

FAISS_METRIC = "cosine"

# ================== INDEX LOGIC ==================

def build_faiss_index(embedding_dir: Path) -> None:
    embeddings_path = embedding_dir / "book_embeddings.pkl"

    if not embeddings_path.exists():
        raise FileNotFoundError(f"Embeddings not found: {embeddings_path}")

    with open(embeddings_path, "rb") as f:
        embeddings = pickle.load(f)

    embeddings = np.asarray(embeddings).astype("float32")

    dim = embeddings.shape[1]

    print(f"Building FAISS index (dim={dim}, size={len(embeddings)})")

    # Cosine similarity via inner product
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)

    index.add(embeddings)

    faiss.write_index(index, str(embedding_dir / "faiss.index"))

    # Save metadata (future-proofing)
    with open(embedding_dir / "index_metadata.pkl", "wb") as f:
        pickle.dump(
            {
                "metric": FAISS_METRIC,
                "dimension": dim,
                "count": len(embeddings)
            },
            f
        )

    print("FAISS index successfully built")
    print(f"Index saved to: {embedding_dir / 'faiss.index'}")

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""FAISS INDEX BUILDER

PURPOSE
-------
Build an ANN index from transformer embeddings
for fast semantic retrieval.

INPUT
-----
- Precomputed transformer embeddings

PROCESSING
----------
1. Load embedding matrix
2. Normalize vectors
3. Build FAISS index (cosine similarity)
4. Persist index to disk

OUTPUT
------
- FAISS index file
- Index metadata

NOT INCLUDED
------------
- No embedding generation
- No recommendation logic
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    parser.add_argument(
        "--embedding-dir",
        type=Path,
        default=PROJECT_ROOT / "storage/embeddings",
        help="Directory containing transformer embeddings"
    )

    args = parser.parse_args()

    build_faiss_index(args.embedding_dir)

if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================
