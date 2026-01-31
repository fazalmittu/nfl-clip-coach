"""Pure pandas filter application — no LLM dependency."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


# ── Schema ──────────────────────────────────────────────────────────────────

class FilterCondition(BaseModel):
    column: str
    operator: str  # eq, neq, gt, lt, gte, lte, contains, not_contains, isin
    value: str | int | float | list


class FilterGroup(BaseModel):
    logic: str  # "and" | "or"
    conditions: list[FilterCondition | FilterGroup]


# ── Data loading ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_data() -> pd.DataFrame:
    csv_path = DATA_DIR / "niners_lions_play_by_play_2023.csv"
    return pd.read_csv(csv_path, low_memory=False)


# ── Filter application ─────────────────────────────────────────────────────

def _apply_condition(df: pd.DataFrame, cond: FilterCondition) -> pd.Series:
    col = df[cond.column]
    op = cond.operator
    val = cond.value

    if op == "eq":
        return col == val
    elif op == "neq":
        return col != val
    elif op == "gt":
        return col > val
    elif op == "lt":
        return col < val
    elif op == "gte":
        return col >= val
    elif op == "lte":
        return col <= val
    elif op == "contains":
        return col.astype(str).str.contains(str(val), case=False, na=False)
    elif op == "not_contains":
        return ~col.astype(str).str.contains(str(val), case=False, na=False)
    elif op == "isin":
        if not isinstance(val, list):
            val = [val]
        return col.isin(val)
    else:
        raise ValueError(f"Unknown operator: {op}")


def _apply_group(df: pd.DataFrame, group: FilterGroup) -> pd.Series:
    masks = []
    for item in group.conditions:
        if isinstance(item, FilterGroup):
            masks.append(_apply_group(df, item))
        else:
            masks.append(_apply_condition(df, item))

    if not masks:
        return pd.Series(True, index=df.index)

    combined = masks[0]
    for m in masks[1:]:
        if group.logic == "and":
            combined = combined & m
        else:
            combined = combined | m
    return combined


def apply_filters(df: pd.DataFrame, filter_group: FilterGroup) -> pd.DataFrame:
    """Apply a FilterGroup to a DataFrame and return matching rows."""
    mask = _apply_group(df, filter_group)
    return df.loc[mask].reset_index(drop=True)
