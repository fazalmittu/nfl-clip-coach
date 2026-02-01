"""clip_search — natural-language to filtered NFL play-by-play data."""

import math
import pandas as pd

from models.schemas import DataQueryResult, GameTimestamp
from services.data import load_data
from .agent import parse_query
from .filter import (
    apply_filters,
    apply_rank,
    apply_sequence,
    apply_drive_filter,
    FilterCondition,
    FilterGroup,
    PlayQuery,
)


def _safe(val):
    """Return None if value is NaN/NaT, else the value."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _safe_int(val):
    v = _safe(val)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _safe_float(val):
    v = _safe(val)
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _safe_str(val):
    v = _safe(val)
    return str(v) if v is not None else None


def _safe_bool(val):
    v = _safe(val)
    if v is None:
        return False
    return bool(int(v))


def _extract_play_data(row) -> dict:
    """Extract key play-by-play fields from a DataFrame row."""
    return {
        "desc": _safe_str(row.get("desc")),
        "play_type": _safe_str(row.get("play_type")),
        "down": _safe_int(row.get("down")),
        "ydstogo": _safe_int(row.get("ydstogo")),
        "yards_gained": _safe_int(row.get("yards_gained")),
        "posteam": _safe_str(row.get("posteam")),
        "defteam": _safe_str(row.get("defteam")),
        "posteam_score": _safe_int(row.get("posteam_score")),
        "defteam_score": _safe_int(row.get("defteam_score")),
        "passer_player_name": _safe_str(row.get("passer_player_name")),
        "rusher_player_name": _safe_str(row.get("rusher_player_name")),
        "receiver_player_name": _safe_str(row.get("receiver_player_name")),
        "touchdown": _safe_bool(row.get("touchdown")),
        "interception": _safe_bool(row.get("interception")),
        "sack": _safe_bool(row.get("sack")),
        "fumble": _safe_bool(row.get("fumble")),
        "yardline_100": _safe_int(row.get("yardline_100")),
        "wpa": _safe_float(row.get("wpa")),
    }


def _ts_from_row(row) -> GameTimestamp:
    return GameTimestamp(
        quarter=int(row["qtr"]),
        time=str(row["time"]) if pd.notna(row["time"]) else "0:00",
        play_data=_extract_play_data(row),
    )


def query(nl_query: str) -> DataQueryResult:
    """Parse a natural-language query and return matching GameTimestamps."""
    play_query = parse_query(nl_query)
    df = load_data()
    df = df.sort_values(["game_id", "play_id"]).reset_index(drop=True)

    timestamps: list[GameTimestamp] = []

    if play_query.type == "filter":
        results = apply_filters(df, play_query.filters)
        if play_query.rank is not None:
            results = apply_rank(results, play_query.rank).reset_index(drop=True)
        for _, row in results.iterrows():
            timestamps.append(_ts_from_row(row))

    elif play_query.type == "sequence":
        if play_query.rank is not None:
            df = apply_rank(df, play_query.rank).reset_index(drop=True)
        spans = apply_sequence(df, play_query.anchor, play_query.then or [])
        for start_idx, end_idx in spans:
            timestamps.append(_ts_from_row(df.iloc[start_idx]))

    elif play_query.type == "drive":
        if play_query.rank is not None:
            df = apply_rank(df, play_query.rank).reset_index(drop=True)
        spans = apply_drive_filter(df, play_query.drive_filter)
        for start_idx, end_idx in spans:
            timestamps.append(_ts_from_row(df.iloc[start_idx]))

    return DataQueryResult(timestamps=timestamps)
