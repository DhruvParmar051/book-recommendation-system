"""
Advanced Transformer-Based Recommendation Script

This script performs high-performance book recommendation using
a two-stage transformer architecture:

1. Bi-encoder for fast semantic retrieval (ANN via FAISS)
2. Cross-encoder for precision reranking
3. Metadata-aware hybrid scoring

This file represents an ADVANCED INFERENCE stage of the
transformer-based recommendation system.
"""

import argparse
import pickle
import faiss
import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder
# ================== MODEL CONFIG ==================

BI_ENCODER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ================== LOADERS ==================

def load_faiss_index(embedding_dir: Path):
    index_path = embedding_dir / "faiss.index"
    meta_path = embedding_dir / "index_metadata.pkl"

    if not index_path.exists():
        raise FileNotFoundError("FAISS index not found")

    if not meta_path.exists():
        raise FileNotFoundError("Index metadata not found")

    index = faiss.read_index(str(index_path))
    with open(meta_path, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata

# ================== HYBRID SCORING ==================

def extract_page_count(pages):
    if not isinstance(pages, str):
        return 0
    import re
    m = re.search(r"\d+", pages)
    return float(m.group()) if m else 0


def hybrid_score(df):
    df = df.copy()

    df["depth_score"] = df["pages"].apply(extract_page_count) / 1000.0

    if "summary" in df.columns:
        df["summary_bonus"] = df["summary"].notna().astype(int)
    else:
        df["summary_bonus"] = 0

    df["final_score"] = (
        0.65 * df["cross_score"]
        + 0.25 * df["depth_score"]
        + 0.10 * df["summary_bonus"]
    )

    return df.sort_values("final_score", ascending=False)

# ================== RECOMMENDATION CORE ==================

class AdvancedTransformerRecommender:
    def __init__(self, data_csv: Path, embedding_dir: Path):
        self.books_df = pd.read_csv(data_csv)

        self.bi_encoder = SentenceTransformer(BI_ENCODER_MODEL)
        self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)

        self.faiss_index, self.index_map = load_faiss_index(embedding_dir)

    def recommend(self, query: str, top_k=5, candidate_pool=100):
        # ---- Stage 1: Bi-encoder ANN search ----
        query_vec = self.bi_encoder.encode(
            [query], normalize_embeddings=True
        ).astype("float32")

        scores, indices = self.faiss_index.search(query_vec, candidate_pool)
        candidate_ids = indices[0]

        candidates = self.books_df.iloc[candidate_ids].copy()

        # ---- Stage 2: Cross-encoder reranking ----
        pairs = [
        (
            query,
            f"{row['title']} {row.get('subjects','')} {row.get('publisher','')}"
        )
        for _, row in candidates.iterrows()
        ]

        cross_scores = self.cross_encoder.predict(pairs)
        candidates["cross_score"] = cross_scores

        # ---- Stage 3: Hybrid metadata reranking ----
        ranked = hybrid_score(candidates)

        return ranked.head(top_k)

# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""ADVANCED TRANSFORMER-BASED BOOK RECOMMENDER

PURPOSE
-------
High-performance book recommendation using a
two-stage transformer architecture.

ARCHITECTURE
------------
1. Bi-encoder + FAISS for fast retrieval
2. Cross-encoder for precision reranking
3. Metadata-aware hybrid scoring

OUTPUT
------
- Highly relevant, ranked book recommendations

NOT INCLUDED
------------
- No ETL logic
- No embedding generation
- No model training
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

    recommender = AdvancedTransformerRecommender(
        data_csv=args.input_csv,
        embedding_dir=args.embedding_dir
    )

    results = recommender.recommend(
        query=args.query,
        top_k=args.top_k
    )

    print("\nRECOMMENDATIONS\n----------------")
    for _, row in results.iterrows():
        print(
            f"- {row['title']} (score={row['final_score']:.3f})"
        )

if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================
