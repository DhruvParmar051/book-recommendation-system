"""
Advanced Transformer-Based Recommendation Engine (FAST VERSION)

This module implements a high-performance, production-style
book recommendation engine using a layered transformer architecture.

ARCHITECTURE
------------
1. Bi-encoder (SentenceTransformer)
   - Encodes query into dense vector
   - Uses FAISS for ultra-fast ANN retrieval

2. Cross-encoder (MiniLM)
   - Reranks top-N candidates precisely
   - Applied only to a small candidate pool

3. Lightweight hybrid scoring
   - Metadata-aware adjustments
   - No heavy pandas loops

PERFORMANCE DESIGN
------------------
- Models loaded once
- Offline-safe (local_files_only=True)
- Cached embeddings
- Small rerank pool
- No recomputation

THIS FILE IS:
-------------
✔ Inference-only
✔ ETL-agnostic
✔ API-safe
"""

from pathlib import Path
import pickle
import re

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, CrossEncoder


# ======================================================
# MODEL CONFIG
# ======================================================

BI_ENCODER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

CANDIDATE_POOL = 30   # 🔥 critical for speed


# ======================================================
# FAISS LOADERS
# ======================================================

def load_faiss_index(embedding_dir: Path):
    """
    Load FAISS index + row mapping.
    """
    index_path = embedding_dir / "faiss.index"
    meta_path = embedding_dir / "index_metadata.pkl"

    if not index_path.exists():
        raise FileNotFoundError("FAISS index not found")

    if not meta_path.exists():
        raise FileNotFoundError("Index metadata not found")

    index = faiss.read_index(str(index_path))
    with open(meta_path, "rb") as f:
        index_map = pickle.load(f)

    return index, index_map


# ======================================================
# HELPER FUNCTIONS
# ======================================================

def extract_page_count(pages):
    """
    Extract numeric page count for depth heuristic.
    """
    if not isinstance(pages, str):
        return 0.0

    m = re.search(r"\d+", pages)
    return float(m.group()) if m else 0.0


def safe_str(val):
    """
    Convert NaN → None for API safety.
    """
    if val is None:
        return None
    if pd.isna(val):
        return None

    val = str(val).strip()
    return val if val else None

def safe_col(row, col):
    """
    Safely read a column from a pandas row.
    Returns empty string if column is missing or NaN.
    """
    if col not in row:
        return ""
    val = row[col]
    if pd.isna(val):
        return ""
    return str(val)


# ======================================================
# RECOMMENDER CORE
# ======================================================

class AdvancedTransformerRecommender:
    """
    High-performance transformer recommender.
    """

    def __init__(self, data_csv: Path, embedding_dir: Path):
        # ------------------------------
        # Load book metadata
        # ------------------------------
        self.books_df = pd.read_csv(data_csv)

        # Clean NaNs once (important for API)
        self.books_df = self.books_df.fillna("")

        # ------------------------------
        # Load models (OFFLINE SAFE)
        # ------------------------------
        self.bi_encoder = SentenceTransformer(
            BI_ENCODER_MODEL,
            local_files_only=True
        )

        self.cross_encoder = CrossEncoder(
            CROSS_ENCODER_MODEL,
            local_files_only=True
        )

        # ------------------------------
        # Load FAISS index
        # ------------------------------
        self.faiss_index, self.index_map = load_faiss_index(embedding_dir)

        # ------------------------------
        # Warm-up (prevents slow first call)
        # ------------------------------
        self._warmup()

    # --------------------------------------------------
    # Internal warmup
    # --------------------------------------------------

    def _warmup(self):
        _ = self.bi_encoder.encode(
            ["machine learning"],
            normalize_embeddings=True
        )

    # --------------------------------------------------
    # Recommendation API
    # --------------------------------------------------

    def recommend(self, query: str, top_k: int = 5) -> pd.DataFrame:
        """
        Recommend top-k books for a free-text query.
        """

        # ------------------------------
        # Stage 1: Bi-encoder retrieval
        # ------------------------------
        query_vec = self.bi_encoder.encode(
            [query],
            normalize_embeddings=True
        ).astype("float32")

        scores, indices = self.faiss_index.search(
            query_vec,
            CANDIDATE_POOL
        )

        candidate_ids = indices[0]
        candidates = self.books_df.iloc[candidate_ids].copy()

        # ------------------------------
        # Stage 2: Cross-encoder rerank
        # ------------------------------
        pairs = [
    (
        query,
        " ".join([
            safe_col(row, "title"),
            safe_col(row, "subjects"),
            safe_col(row, "publisher"),
            safe_col(row, "authors"),
        ])
    )
    for _, row in candidates.iterrows()
]


        cross_scores = self.cross_encoder.predict(pairs)
        candidates["cross_score"] = cross_scores

        # ------------------------------
        # Stage 3: Lightweight hybrid score
        # ------------------------------
        candidates["depth_score"] = (
            candidates["pages"]
            .apply(extract_page_count)
            / 1000.0
        )

        candidates["final_score"] = (
            0.8 * candidates["cross_score"]
            + 0.2 * candidates["depth_score"]
        )

        ranked = candidates.sort_values(
            "final_score",
            ascending=False
        )

        # ------------------------------
        # Final formatting (API-safe)
        # ------------------------------
        result = ranked.head(top_k).copy()

        for col in result.columns:
            result[col] = result[col].apply(safe_str)

        return result


# ======================================================
# CLI (OPTIONAL TESTING)
# ======================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="""
ADVANCED TRANSFORMER BOOK RECOMMENDER (FAST)

PURPOSE
-------
High-speed semantic book recommendation using:
- Transformer bi-encoder
- FAISS ANN search
- Cross-encoder reranking

USAGE
-----
python recommender/advanced_transformer_recommender.py \
    --query "data mining" \
    --top-k 5
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    parser.add_argument(
        "--input-csv",
        type=Path,
        default=PROJECT_ROOT / "data/processed_data/books_features.csv"
    )

    parser.add_argument(
        "--embedding-dir",
        type=Path,
        default=PROJECT_ROOT / "storage/embeddings"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5
    )

    args = parser.parse_args()

    rec = AdvancedTransformerRecommender(
        data_csv=args.input_csv,
        embedding_dir=args.embedding_dir
    )

    results = rec.recommend(args.query, args.top_k)

    print("\nRECOMMENDATIONS\n----------------")
    for _, row in results.iterrows():
        print(
            f"- {row['title']} (score={row['final_score']})"
        )


if __name__ == "__main__":
    main()

# ================== END OF FILE ==================
