from datasets import load_dataset
from pathlib import Path

def load_books_dataset(dataset_name: str, cache_dir: Path) -> Path:
    ds = load_dataset(
        dataset_name,
        split="train",
        cache_dir=str(cache_dir)
    )

    # HF stores files here
    snapshot_dir = Path(ds.cache_files[0]["filename"]).parent
    return snapshot_dir
