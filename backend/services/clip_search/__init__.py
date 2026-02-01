"""clip_search — natural-language to filtered NFL play-by-play data."""

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


MIN_DURATION = 10.0


def _compute_durations(df: pd.DataFrame) -> pd.Series:
    """Estimate play duration from game clock delta to the next play.

    Uses the difference in game_seconds_remaining between consecutive
    plays in the same game. Short clips are floored to 10s so they're
    still useful. Last play of a game defaults to 10s.
    """
    df = df.sort_values(["game_id", "play_id"])
    next_seconds = df.groupby("game_id")["game_seconds_remaining"].shift(-1)
    duration = df["game_seconds_remaining"] - next_seconds
    duration = duration.clip(lower=MIN_DURATION)
    duration = duration.fillna(MIN_DURATION)
    return duration


def _span_duration(df: pd.DataFrame, start_idx: int, end_idx: int) -> float:
    """Duration covering a span of plays (start through end + buffer)."""
    start_secs = df.iloc[start_idx]["game_seconds_remaining"]
    end_secs = df.iloc[end_idx]["game_seconds_remaining"]
    dur = start_secs - end_secs + 10
    return max(dur, MIN_DURATION)


def _timestamp_from_row(row) -> GameTimestamp:
    return GameTimestamp(
        quarter=int(row["qtr"]),
        time=str(row["time"]) if pd.notna(row["time"]) else "0:00",
        duration_seconds=float(row["_duration"]) if "_duration" in row.index else MIN_DURATION,
    )


def query(nl_query: str) -> DataQueryResult:
    """Parse a natural-language query and return matching GameTimestamps."""
    play_query = parse_query(nl_query)
    df = load_data()
    df = df.sort_values(["game_id", "play_id"]).reset_index(drop=True)

    timestamps: list[GameTimestamp] = []

    if play_query.type == "filter":
        df = df.assign(_duration=_compute_durations(df))
        results = apply_filters(df, play_query.filters)
        if play_query.rank is not None:
            results = apply_rank(results, play_query.rank).reset_index(drop=True)
        for _, row in results.iterrows():
            timestamps.append(_timestamp_from_row(row))

    elif play_query.type == "sequence":
        if play_query.rank is not None:
            df = apply_rank(df, play_query.rank).reset_index(drop=True)
        spans = apply_sequence(df, play_query.anchor, play_query.then or [])
        for start_idx, end_idx in spans:
            row = df.iloc[start_idx]
            timestamps.append(
                GameTimestamp(
                    quarter=int(row["qtr"]),
                    time=str(row["time"]) if pd.notna(row["time"]) else "0:00",
                    duration_seconds=_span_duration(df, start_idx, end_idx),
                )
            )

    elif play_query.type == "drive":
        if play_query.rank is not None:
            df = apply_rank(df, play_query.rank).reset_index(drop=True)
        spans = apply_drive_filter(df, play_query.drive_filter)
        for start_idx, end_idx in spans:
            row = df.iloc[start_idx]
            timestamps.append(
                GameTimestamp(
                    quarter=int(row["qtr"]),
                    time=str(row["time"]) if pd.notna(row["time"]) else "0:00",
                    duration_seconds=_span_duration(df, start_idx, end_idx),
                )
            )

    return DataQueryResult(timestamps=timestamps)
