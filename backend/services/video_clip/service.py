"""
Video Clip Service

Takes game timestamps and returns VOD clip timestamps.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import GameTimestamp, ClipTimestamp
from .indexer import VideoIndexer


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
    indexer = VideoIndexer(video_path)

    try:
        # Auto-index if needed
        if not indexer.index.is_indexed:
            print(f"No index found for {video_path}, running auto-index...")
            indexer.auto_index()

        clips = []
        for ts in timestamps:
            print(f"\nProcessing: Q{ts.quarter} {ts.time}")

            start = indexer.find_vod_timestamp(ts.quarter, ts.time)
            end = start + ts.duration_seconds + play_buffer_seconds

            clips.append(ClipTimestamp(
                start_time=start,
                end_time=end,
                video_path=video_path
            ))

        return clips

    finally:
        indexer.close()


if __name__ == "__main__":
    # Quick test
    video = "data/49ers-Lions.mp4"

    test_timestamps = [
        GameTimestamp(quarter=2, time="8:34", duration_seconds=5.0),
        GameTimestamp(quarter=3, time="5:00", duration_seconds=7.0),
    ]

    print("=== Video Clip Service Test ===\n")
    clips = get_clips(video, test_timestamps)

    print("\n=== Results ===")
    for i, clip in enumerate(clips):
        print(f"\nClip {i + 1}:")
        print(f"  Start: {clip.start_time:.1f}s ({clip.start_time/60:.1f} min)")
        print(f"  End: {clip.end_time:.1f}s ({clip.end_time/60:.1f} min)")
        print(f"  Duration: {clip.end_time - clip.start_time:.1f}s")
