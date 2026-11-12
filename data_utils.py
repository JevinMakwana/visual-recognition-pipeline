"""Locate the A2 dataset, downloading it from Google Drive if it is missing.

The dataset is a single zip on Google Drive (anyone with the link can view):
    https://drive.google.com/file/d/1YH4ePf17TTYU_wh2Rc5BF3ZhGmn42Cw7/view

A zip is used because Google Drive folder downloads stop at 50 files per folder,
and train/images alone has 2200.

Usage in a notebook (run from the repo root):
    from data_utils import ensure_dataset
    DATA_ROOT = ensure_dataset()   # -> <repo>/data/Dataset
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

# Drive file ID of MLDS-A2-data.zip (the part after /file/d/ in its share link).
DATASET_ZIP_ID = "1YH4ePf17TTYU_wh2Rc5BF3ZhGmn42Cw7"

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


def is_dataset_dir(path: Path) -> bool:
    """True if `path` looks like a complete Dataset/ folder."""
    return (
        (path / "train" / "images").is_dir()
        and (path / "train" / "segmentation_masks").is_dir()
        and (path / "train" / "labels.csv").is_file()
        and (path / "test" / "images").is_dir()
    )


def ensure_dataset(data_dir: Path | str = DEFAULT_DATA_DIR) -> Path:
    """Return `data_dir/Dataset`, downloading and extracting it first if missing."""
    data_dir = Path(data_dir)
    dataset = data_dir / "Dataset"
    if is_dataset_dir(dataset):
        return dataset

    try:
        import gdown
    except ImportError as e:
        raise ImportError("Dataset not found locally; install gdown to download it: pip install gdown") from e

    print(f"Dataset not found at {dataset}; downloading from Google Drive...", flush=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = data_dir / "MLDS-A2-data.zip"
    if not zip_path.exists():
        part = zip_path.with_suffix(".zip.part")
        out = gdown.download(id=DATASET_ZIP_ID, output=str(part), quiet=False)
        if out is None:
            raise RuntimeError(
                "Google Drive download failed. Check that the zip is shared as "
                "'Anyone with the link', or download it manually into " + str(data_dir)
            )
        part.replace(zip_path)

    # Extract into a staging folder so an interrupted run never leaves a half-filled Dataset/.
    staging = data_dir / "_extracting"
    shutil.rmtree(staging, ignore_errors=True)
    print(f"Extracting {zip_path.name}...", flush=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(staging)

    if not is_dataset_dir(staging / "Dataset"):
        raise RuntimeError(f"{zip_path} does not contain a valid Dataset/ folder.")
    if dataset.exists():
        shutil.rmtree(dataset)  # incomplete leftover
    (staging / "Dataset").replace(dataset)
    for extra in staging.iterdir():  # README files that ship with the dataset
        target = data_dir / extra.name
        if not target.exists():
            extra.replace(target)
    shutil.rmtree(staging, ignore_errors=True)
    zip_path.unlink()

    print(f"Dataset ready at {dataset}", flush=True)
    return dataset


if __name__ == "__main__":
    print(ensure_dataset())
