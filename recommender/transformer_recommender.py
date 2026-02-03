"""
Transformer-Based Recommendation Script

This script performs the ONLINE recommendation stage using
precomputed transformer embeddings. It accepts a free-text
user query, embeds it using the same transformer model, and
retrieves semantically relevant books.

In addition to semantic similarity, it applies a hybrid
re-ranking strategy using structured metadata signals such as
book depth and summary availability.

This file represents the INFERENCE stage of the
transformer-based recommendation system.
"""

import argparse
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ================== MODEL CONFIG ==================

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ================== LOADERS ==================

def load_embedding_index(embedding_dir: Path):
    """
    Load transformer embedding matrix and index mapping.
    """
    embeddings_path = embedding_dir / "book_embeddings.pkl"
    index_path = embedding_dir / "embedding_index.csv"

    if not embeddings_path.exists():
        raise FileNotFoundError(f"Missing embeddings file: {embeddings_path}")

    if not index_path.exists():
        raise FileNotFoundError(f"Missing index file: {index_path}")

    with open(embeddings_path, "rb") as f:
        embeddings = pickle.load(f)

    index_df = pd.read_csv(index_path)

    return embeddings, index_df


# ================== SCORING UTILITIES ==================

def extract_page_count(pages):
    """
    Extract numeric page count from pages string.
    """
    if not isinstance(pages, str):
        return None

    nums = pd.Series(pages).str.extract(r"(\d+)")[0]
    if nums.isna().all():
        return None

    return float(nums.iloc[0])


def hybrid_rerank(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply hybrid re-ranking using structured metadata.

    Signals:
    - Semantic similarity (primary)
    - Page depth (secondary)
    - Summary availability (optional bonus)
    """
    df = df.copy()

    # Depth score (normalized)
    df["page_count"] = df["pages"].apply(extract_page_count)
    df["depth_score"] = df["page_count"].fillna(0) / 1000.0

    # Summary bonus (ONLY if column exists)
    if "summary" in df.columns:
        df["summary_bonus"] = df["summary"].notna().astype(int)
    else:
        df["summary_bonus"] = 0

    # Final hybrid score
    df["final_score"] = (
        0.70 * df["semantic_score"]
        + 0.20 * df["depth_score"]
        + 0.10 * df["summary_bonus"]
    )

    return df.sort_values("final_score", ascending=False)


# ================== RECOMMENDATION LOGIC ==================

def recommend_books(
    query: str,
    embeddings: np.ndarray,
    books_df: pd.DataFrame,
    model: SentenceTransformer,
    top_k: int,
    candidate_pool: int = 50
) -> pd.DataFrame:
    """
    Perform semantic retrieval followed by hybrid re-ranking.
    """
    query_vec = model.encode(
        [query],
        normalize_embeddings=True
    )

    similarity_scores = cosine_similarity(query_vec, embeddings)[0]

    # Candidate recall (semantic)
    top_indices = np.argsort(similarity_scores)[-candidate_pool:][::-1]
    candidates = books_df.iloc[top_indices].copy()
    candidates["semantic_score"] = similarity_scores[top_indices]

    # Hybrid re-ranking
    ranked = hybrid_rerank(candidates)

    return ranked.head(top_k)


# ================== PIPELINE ENTRY ==================

def run_recommendation(
    input_csv: Path,
    embedding_dir: Path,
    query: str,
    top_k: int,
    model_name: str
) -> pd.DataFrame:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    if not embedding_dir.exists():
        raise FileNotFoundError(f"Embedding directory not found: {embedding_dir}")

    books_df = pd.read_csv(input_csv)
    embeddings, _ = load_embedding_index(embedding_dir)

    if len(books_df) != len(embeddings):
        raise ValueError("Mismatch between embeddings and book records")

    model = SentenceTransformer(model_name)

    return recommend_books(
        query=query,
        embeddings=embeddings,
        books_df=books_df,
        model=model,
        top_k=top_k
    )


# ================== CLI ==================

def main():
    parser = argparse.ArgumentParser(
        description=
"""TRANSFORMER-BASED BOOK RECOMMENDER

PURPOSE
-------
Recommend books using semantic similarity powered
by pretrained transformer embeddings, enhanced with
structured metadata re-ranking.

INPUT
-----
- Precomputed transformer embeddings
- Recommender-ready feature CSV
- Free-text user query

PROCESSING
----------
1. Encode user query using transformer
2. Retrieve semantically similar books
3. Re-rank results using metadata signals
4. Return top-K recommendations

OUTPUT
------
- Ranked list of recommended books printed to stdout

NOT INCLUDED
------------
- No ETL logic
- No embedding construction
- No model training
- No database writes
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    parser.add_argument(
        "--input-csv",
        type=Path,
        default=PROJECT_ROOT / "data/processed_data/books_features.csv",
        help="Recommender-ready feature CSV"
    )

    parser.add_argument(
        "--embedding-dir",
        type=Path,
        default=PROJECT_ROOT / "storage/embeddings",
        help="Directory containing transformer embeddings"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Free-text description of the book or topic"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of recommendations to return (default: 5)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Transformer model name (default: {DEFAULT_MODEL})"
    )

    args = parser.parse_args()

    results = run_recommendation(
        input_csv=args.input_csv,
        embedding_dir=args.embedding_dir,
        query=args.query,
        top_k=args.top_k,
        model_name=args.model
    )

    print("\nRECOMMENDATIONS\n----------------")
    for _, row in results.iterrows():
        print(
            f"- {row['title']} "
            f"(score={row['final_score']:.3f})"
        )


if __name__ == "__main__":
    main()

# ================== END OF SCRIPT ==================
