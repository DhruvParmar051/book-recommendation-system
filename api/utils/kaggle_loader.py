import os
import subprocess
from pathlib import Path

DATA_DIR = Path("assets")

def download_kaggle_dataset():
    if (DATA_DIR / "books_features.csv").exists():
        return  # already downloaded

    DATA_DIR.mkdir(exist_ok=True)

    subprocess.run(
        [
            "kaggle",
            "datasets",
            "download",
            "-d",
            "dhruvparmar/book-recommender-assets",
            "-p",
            str(DATA_DIR),
            "--unzip"
        ],
        check=True
    )
