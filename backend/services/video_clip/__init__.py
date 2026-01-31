def __getattr__(name):
    """Lazy imports to avoid circular import issues when running as __main__."""
    if name in ("VideoIndexer", "VideoIndex", "GameClock"):
        from . import indexer
        return getattr(indexer, name)
    if name == "get_clips":
        from .service import get_clips
        return get_clips
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["VideoIndexer", "VideoIndex", "GameClock", "get_clips"]
