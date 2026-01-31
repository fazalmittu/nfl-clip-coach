def __getattr__(name):
    """Lazy imports to avoid circular import issues when running as __main__."""
    if name in ("VideoIndexer", "TimelineIndex", "QuarterBoundary",
                "GameClock", "TimestampCache", "TimestampMapping"):
        from . import indexer
        return getattr(indexer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "VideoIndexer",
    "TimelineIndex",
    "QuarterBoundary",
    "GameClock",
    "TimestampCache",
    "TimestampMapping",
]
