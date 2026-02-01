"""Data loading utilities."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_data() -> pd.DataFrame:
    csv_path = DATA_DIR / "niners_lions_play_by_play_2023.csv"
    return pd.read_csv(csv_path, low_memory=False)
