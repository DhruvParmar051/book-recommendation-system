from pathlib import Path
from huggingface_hub import hf_hub_download
import pandas as pd

ASSET_FILES = [
    "books_features.csv",
    "faiss.index",
    "index_metadata.pkl",
]

def load_books_dataset(dataset_name: str, cache_dir: Path) -> pd.DataFrame:
    """
    Download CSV + FAISS assets from Hugging Face dataset repo
    into a stable local directory.

    Returns pandas DataFrame.
    """

    assets_dir = cache_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for filename in ASSET_FILES:
        hf_hub_download(
            repo_id=dataset_name,
            filename=filename,
            repo_type="dataset",
            local_dir=assets_dir,
            local_dir_use_symlinks=False,  # IMPORTANT for Windows + Render
        )

    csv_path = assets_dir / "books_features.csv"
    return pd.read_csv(csv_path)
