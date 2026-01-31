"""data_query — natural-language to filtered NFL play-by-play data."""

import pandas as pd

from models.schemas import DataQueryResult, GameTimestamp
from .agent import parse_query
from .filter import apply_filters, load_data, FilterCondition, FilterGroup


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


def query(nl_query: str) -> DataQueryResult:
    """Parse a natural-language query and return matching GameTimestamps."""
    filters = parse_query(nl_query)
    df = load_data()
    # Compute durations on full df before filtering (needs neighboring rows)
    df = df.assign(_duration=_compute_durations(df))
    results = apply_filters(df, filters)

    timestamps = []
    for _, row in results.iterrows():
        timestamps.append(
            GameTimestamp(
                quarter=int(row["qtr"]),
                time=str(row["time"]) if pd.notna(row["time"]) else "0:00",
                duration_seconds=float(row["_duration"]),
            )
        )

    return DataQueryResult(timestamps=timestamps)
