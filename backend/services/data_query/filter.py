"""Pure pandas filter application — no LLM dependency."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel


# ── Schema ──────────────────────────────────────────────────────────────────

class FilterCondition(BaseModel):
    column: str
    operator: str  # eq, neq, gt, lt, gte, lte, contains, not_contains, isin
    value: str | int | float | list | None


class FilterGroup(BaseModel):
    logic: str  # "and" | "or"
    conditions: list[FilterCondition | FilterGroup]


class SequenceStep(BaseModel):
    filters: FilterGroup
    scope: Literal["next_play", "same_drive", "next_drive"]


class RankFilter(BaseModel):
    group_by: list[str] = []
    rank_column: str
    rank_order: Literal["asc", "desc"]
    rank: int = 1


class DrivePlayPosition(BaseModel):
    position: int  # 1-indexed: 1 = first play, 2 = second, etc.
    filters: FilterGroup


class DriveFilter(BaseModel):
    include: FilterGroup | None = None
    include_min_count: int = 1
    exclude: FilterGroup | None = None
    play_at: DrivePlayPosition | None = None


class PlayQuery(BaseModel):
    """Top-level query — LLM picks the type."""
    type: Literal["filter", "sequence", "drive"]
    filters: FilterGroup | None = None
    anchor: FilterGroup | None = None
    then: list[SequenceStep] | None = None
    drive_filter: DriveFilter | None = None
    rank: RankFilter | None = None


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

    if val is None:
        if op == "eq":
            return col.isna()
        elif op == "neq":
            return col.notna()
        else:
            return pd.Series(False, index=df.index)

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


# ── Rank pre-filter ───────────────────────────────────────────────────────

def apply_rank(df: pd.DataFrame, rank_filter: RankFilter) -> pd.DataFrame:
    ascending = rank_filter.rank_order == "asc"
    df = df.sort_values(rank_filter.rank_column, ascending=ascending)
    if not rank_filter.group_by:
        # No grouping — just take the Nth row overall
        idx = rank_filter.rank - 1
        if idx >= len(df):
            return df.iloc[0:0]
        return df.iloc[idx: idx + 1]
    ranked = df.groupby(rank_filter.group_by, sort=False).nth(rank_filter.rank - 1)
    return df[df.index.isin(ranked.index)]


# ── Sequence matching ─────────────────────────────────────────────────────

def apply_sequence(
    df: pd.DataFrame,
    anchor: FilterGroup,
    steps: list[SequenceStep],
) -> list[tuple[int, int]]:
    """Return (anchor_iloc, end_iloc) pairs for matched sequences."""
    df = df.sort_values(["game_id", "play_id"]).reset_index(drop=True)
    anchor_mask = _apply_group(df, anchor)
    anchor_idxs = df.index[anchor_mask].tolist()

    results: list[tuple[int, int]] = []
    for a_idx in anchor_idxs:
        a_row = df.iloc[a_idx]
        cur_idx = a_idx
        matched = True
        for step in steps:
            if step.scope == "next_play":
                nxt = cur_idx + 1
                if nxt >= len(df):
                    matched = False
                    break
                nxt_row = df.iloc[nxt]
                if nxt_row["game_id"] != a_row["game_id"]:
                    matched = False
                    break
                if nxt_row["drive"] != a_row["drive"]:
                    matched = False
                    break
                candidate = df.iloc[nxt: nxt + 1]
                if candidate.empty or not _apply_group(candidate, step.filters).any():
                    matched = False
                    break
                cur_idx = nxt

            elif step.scope == "same_drive":
                drive_plays = df[
                    (df["game_id"] == a_row["game_id"])
                    & (df["drive"] == a_row["drive"])
                    & (df.index > cur_idx)
                ]
                if drive_plays.empty:
                    matched = False
                    break
                step_mask = _apply_group(drive_plays, step.filters)
                hits = drive_plays[step_mask]
                if hits.empty:
                    matched = False
                    break
                cur_idx = hits.index[-1]

            elif step.scope == "next_drive":
                cur_drive = df.iloc[cur_idx]["drive"]
                game_plays = df[df["game_id"] == a_row["game_id"]]
                next_drives = game_plays[game_plays["drive"] > cur_drive]
                if next_drives.empty:
                    matched = False
                    break
                next_drive_num = next_drives["drive"].iloc[0]
                next_drive_plays = next_drives[next_drives["drive"] == next_drive_num]
                step_mask = _apply_group(next_drive_plays, step.filters)
                hits = next_drive_plays[step_mask]
                if hits.empty:
                    matched = False
                    break
                cur_idx = hits.index[-1]

        if matched:
            results.append((a_idx, cur_idx))

    return results


# ── Drive filter ──────────────────────────────────────────────────────────

def apply_drive_filter(
    df: pd.DataFrame, drive_filter: DriveFilter
) -> list[tuple[int, int]]:
    """Return (first_play_iloc, last_play_iloc) for each matching drive."""
    df = df.sort_values(["game_id", "play_id"]).reset_index(drop=True)
    groups = df.groupby(["game_id", "drive"], sort=False)

    results: list[tuple[int, int]] = []
    for (_gid, _drv), grp in groups:
        keep = True
        if drive_filter.include is not None:
            mask = _apply_group(grp, drive_filter.include)
            if mask.sum() < drive_filter.include_min_count:
                keep = False
        if keep and drive_filter.play_at is not None:
            pos = drive_filter.play_at.position - 1
            if pos >= len(grp):
                keep = False
            else:
                row_df = grp.iloc[pos: pos + 1]
                if not _apply_group(row_df, drive_filter.play_at.filters).any():
                    keep = False
        if keep and drive_filter.exclude is not None:
            mask = _apply_group(grp, drive_filter.exclude)
            if mask.any():
                keep = False
        if keep:
            results.append((grp.index[0], grp.index[-1]))

    return results
