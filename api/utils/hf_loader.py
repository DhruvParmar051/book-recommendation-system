from datasets import load_dataset
from pathlib import Path
import pandas as pd

def load_books_dataset(
    dataset_name: str,
    split: str = "train",
    cache_dir: Path | None = None,
):
    """
    Load books dataset from Hugging Face and return a pandas DataFrame.
    Cached locally for reuse (Render-safe).
    """
    ds = load_dataset(
        dataset_name,
        split=split,
        cache_dir=str(cache_dir) if cache_dir else None
    )

    df = ds.to_pandas()
    return df
