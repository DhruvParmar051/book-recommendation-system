"""
Advanced Transformer-Based Recommendation Engine (LOW-RAM VERSION)

Designed explicitly for:
- Render Free tier (512 MB)
- CPU-only inference
- Lazy loading
- FAISS + MiniLM only

REMOVED:
- Cross-encoder
- Pandas DataFrame retention
- Warmup
- Hybrid metadata scoring

KEPT:
- Transformer bi-encoder
- FAISS ANN search
- Inference-only API
"""

from pathlib import Path
import pickle
import gc

import numpy as np
import faiss
import torch
from sentence_transformers import SentenceTransformer

# ======================================================
# HARD MEMORY LIMITS (CRITICAL)
# ======================================================

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

BI_ENCODER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ======================================================
# RECOMMENDER
# ======================================================

class AdvancedTransformerRecommender:
    """
    Ultra-low RAM semantic recommender.
    """

    def __init__(self, data_csv: Path, embedding_dir: Path):
        """
        DO NOT load models, FAISS, or data here.
        Only store paths.
        """

        self.embedding_dir = embedding_dir
        self.index_path = embedding_dir / "faiss.index"
        self.meta_path = embedding_dir / "index_metadata.pkl"

        self._model = None
        self._index = None
        self._record_ids = None

    # ==================================================
    # LAZY MODEL LOAD
    # ==================================================

    def _load_model(self):
        if self._model is None:
            print("🧠 Loading MiniLM bi-encoder (low RAM)...")

            self._model = SentenceTransformer(
                BI_ENCODER_MODEL,
                device="cpu"
            )

            gc.collect()

        return self._model

    # ==================================================
    # LAZY FAISS LOAD
    # ==================================================

    def _load_faiss(self):
        if self._index is None:
            print("📦 Loading FAISS index...")

            self._index = faiss.read_index(str(self.index_path))

            with open(self.meta_path, "rb") as f:
                meta = pickle.load(f)

            # Expect ONLY record_id list
            self._record_ids = meta["record_ids"]

            del meta
            gc.collect()

        return self._index

    # ==================================================
    # QUERY EMBEDDING
    # ==================================================

    def _embed_query(self, query: str) -> np.ndarray:
        model = self._load_model()

        vec = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return vec.astype("float32")

    # ==================================================
    # PUBLIC API
    # ==================================================

    def recommend(self, query: str, top_k: int = 5):
        """
        Return minimal recommendation results.

        Output format:
        [
          {"record_id": "...", "final_score": 0.82},
          ...
        ]
        """

        index = self._load_faiss()
        query_vec = self._embed_query(query)

        scores, indices = index.search(query_vec, top_k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue

            results.append({
                "record_id": self._record_ids[idx],
                "final_score": float(score)
            })

        gc.collect()
        return results
