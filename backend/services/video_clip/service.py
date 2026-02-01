"""
Video Clip Service

Takes game timestamps and returns VOD clip timestamps.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import GameTimestamp, ClipTimestamp
from .indexer import VideoIndexer

PRE_PLAY_PADDING = 5  # seconds before clock-match to start clip

# Base clip durations by play_type (seconds of video after start point)
PLAY_TYPE_DURATIONS: dict[str, float] = {
    "pass":         20,
    "run":          20,
    "kickoff":      25,
    "punt":         25,
    "field_goal":   20,
    "extra_point":  15,
    "no_play":      15,
    "qb_kneel":     10,
    "qb_spike":     10,
}
DEFAULT_CLIP_DURATION = 20  # fallback for unknown play_type

TOUCHDOWN_BONUS = 25.0   # celebration + replay + XP setup
TURNOVER_BONUS  = 15.0   # INT/fumble return + aftermath


def _get_clip_duration(play_data: dict) -> float:
    """Compute clip duration based on play type and event flags."""
    play_type = play_data.get("play_type") or ""
    base = PLAY_TYPE_DURATIONS.get(play_type, DEFAULT_CLIP_DURATION)

    if play_data.get("touchdown"):
        base += TOUCHDOWN_BONUS
    if play_data.get("interception") or play_data.get("fumble"):
        base += TURNOVER_BONUS

    return base


def get_clips(
    video_path: str,
    timestamps: list[GameTimestamp],
    play_buffer_seconds: float = 15.0,
) -> list[ClipTimestamp]:
    """
    Convert game timestamps to VOD clip timestamps.
    """
    indexer = VideoIndexer(video_path)

    try:
        if not indexer.index.is_indexed:
            indexer.auto_index()

        clips = []
        for ts in timestamps:
            start = max(0, indexer.find_vod_timestamp(ts.quarter, ts.time) - PRE_PLAY_PADDING)
            duration = _get_clip_duration(pd)
            end = start + duration + play_buffer_seconds
            pd = ts.play_data or {}
            clips.append(ClipTimestamp(
                start_time=start,
                end_time=end,
                video_path=video_path,
                description=pd.get("desc"),
                play_type=pd.get("play_type"),
                down=pd.get("down"),
                ydstogo=pd.get("ydstogo"),
                yards_gained=pd.get("yards_gained"),
                posteam=pd.get("posteam"),
                defteam=pd.get("defteam"),
                quarter=ts.quarter,
                game_time=ts.time,
                posteam_score=pd.get("posteam_score"),
                defteam_score=pd.get("defteam_score"),
                passer=pd.get("passer_player_name"),
                rusher=pd.get("rusher_player_name"),
                receiver=pd.get("receiver_player_name"),
                is_touchdown=pd.get("touchdown", False),
                is_interception=pd.get("interception", False),
                is_sack=pd.get("sack", False),
                is_fumble=pd.get("fumble", False),
                yardline_100=pd.get("yardline_100"),
                wpa=pd.get("wpa"),
            ))

        return clips

    finally:
        indexer.close()


if __name__ == "__main__":
    video = "data/49ers-Lions.mp4"
    test_timestamps = [
        GameTimestamp(quarter=2, time="8:34"),
        GameTimestamp(quarter=3, time="5:00"),
    ]

    clips = get_clips(video, test_timestamps)
    for i, clip in enumerate(clips):
        print(f"Clip {i+1}: {clip.start_time:.1f}s")
