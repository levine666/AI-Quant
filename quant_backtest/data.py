"""数据加载辅助。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv(
    path: str | Path,
    *,
    date_col: str = "date",
) -> pd.DataFrame:
    df = pd.read_csv(path)
    df[date_col] = pd.to_datetime(df[date_col])
    return df.sort_values(date_col).reset_index(drop=True)
