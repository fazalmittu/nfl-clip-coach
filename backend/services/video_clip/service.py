"""
Video Clip Service

Takes game timestamps and returns VOD clip timestamps.
"""

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import GameTimestamp, ClipTimestamp
from .indexer import VideoIndexer

logger = logging.getLogger(__name__)


def get_clips(
    video_path: str,
    timestamps: list[GameTimestamp],
    play_buffer_seconds: float = 15.0
) -> list[ClipTimestamp]:
    """
    Convert game timestamps to VOD clip timestamps.

    Args:
        video_path: Path to the video file
        timestamps: List of game timestamps to find
        play_buffer_seconds: Extra seconds to add after play duration

    Returns:
        List of ClipTimestamp objects with VOD start/end times
    """
    logger.info(f"Processing {len(timestamps)} timestamps for {video_path}")
    indexer = VideoIndexer(video_path)

    try:
        # Auto-index if needed
        if not indexer.index.is_indexed:
            logger.info("No index found, running auto-index (this may take a few minutes)...")
            indexer.auto_index()

        clips = []
        for i, ts in enumerate(timestamps):
            logger.info(f"[{i+1}/{len(timestamps)}] Finding Q{ts.quarter} {ts.time}...")

            start = indexer.find_vod_timestamp(ts.quarter, ts.time)
            end = start + ts.duration_seconds + play_buffer_seconds

            logger.info(f"  -> VOD {start:.1f}s - {end:.1f}s ({end-start:.0f}s clip)")

            clips.append(ClipTimestamp(
                start_time=start,
                end_time=end,
                video_path=video_path
            ))

        logger.info(f"Completed: {len(clips)} clips generated")
        return clips

    finally:
        indexer.close()


if __name__ == "__main__":
    # Configure logging for standalone test
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    video = "data/49ers-Lions.mp4"
    test_timestamps = [
        GameTimestamp(quarter=2, time="8:34", duration_seconds=5.0),
        GameTimestamp(quarter=3, time="5:00", duration_seconds=7.0),
    ]

    logger.info("=== Video Clip Service Test ===")
    clips = get_clips(video, test_timestamps)

    logger.info("=== Results ===")
    for i, clip in enumerate(clips):
        logger.info(f"Clip {i+1}: {clip.start_time:.1f}s - {clip.end_time:.1f}s ({clip.end_time - clip.start_time:.0f}s)")
