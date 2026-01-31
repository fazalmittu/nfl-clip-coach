"""
Video Indexer Service

Uses Gemini Vision to build a timeline index of a game video,
mapping game timestamps (Q2 8:34) to VOD timestamps (seconds into video).

Two modes:
1. Manual indexing - provide rough estimates, system refines to exact
2. Automated scanning - system searches for quarter boundaries automatically
"""

from __future__ import annotations

import cv2
import json
import os
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")


@dataclass
class GameClock:
    """Represents a game clock reading from a video frame."""
    quarter: int  # 1-4, 5 for OT
    minutes: int
    seconds: int

    @property
    def time_str(self) -> str:
        return f"{self.minutes}:{self.seconds:02d}"

    @property
    def total_seconds(self) -> int:
        """Total seconds remaining in quarter."""
        return self.minutes * 60 + self.seconds

    def __str__(self) -> str:
        q_str = f"Q{self.quarter}" if self.quarter <= 4 else "OT"
        return f"{q_str} {self.time_str}"


@dataclass
class QuarterBoundary:
    """VOD timestamps for a quarter's start and end."""
    quarter: int
    start_vod_seconds: float  # VOD time when quarter starts (15:00 on clock)
    end_vod_seconds: float | None = None  # VOD time when quarter ends (0:00 on clock)


@dataclass
class TimelineIndex:
    """Complete timeline index for a game video."""
    video_path: str
    quarters: list[QuarterBoundary]
    halftime_start_vod: float | None = None
    halftime_end_vod: float | None = None

    def get_quarter_range(self, quarter: int) -> tuple[float, float] | None:
        """Get VOD time range for a quarter."""
        for q in self.quarters:
            if q.quarter == quarter:
                if q.end_vod_seconds:
                    return (q.start_vod_seconds, q.end_vod_seconds)
                # If no end, estimate based on next quarter or video length
                return (q.start_vod_seconds, q.start_vod_seconds + 3600)  # 1hr fallback
        return None

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "quarters": [asdict(q) for q in self.quarters],
            "halftime_start_vod": self.halftime_start_vod,
            "halftime_end_vod": self.halftime_end_vod,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimelineIndex":
        return cls(
            video_path=data["video_path"],
            quarters=[QuarterBoundary(**q) for q in data["quarters"]],
            halftime_start_vod=data.get("halftime_start_vod"),
            halftime_end_vod=data.get("halftime_end_vod"),
        )


@dataclass
class TimestampMapping:
    """A cached mapping from game time to VOD time."""
    quarter: int
    game_time: str  # "8:34"
    vod_seconds: float


class TimestampCache:
    """Persistent cache of game time -> VOD time mappings."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.mappings: dict[str, TimestampMapping] = {}
        self._load()

    def _make_key(self, quarter: int, game_time: str) -> str:
        return f"Q{quarter}_{game_time}"

    def _load(self):
        if self.cache_path.exists():
            with open(self.cache_path) as f:
                data = json.load(f)
                for key, m in data.items():
                    self.mappings[key] = TimestampMapping(**m)

    def _save(self):
        with open(self.cache_path, "w") as f:
            json.dump({k: asdict(v) for k, v in self.mappings.items()}, f, indent=2)

    def get(self, quarter: int, game_time: str) -> TimestampMapping | None:
        return self.mappings.get(self._make_key(quarter, game_time))

    def set(self, quarter: int, game_time: str, vod_seconds: float):
        key = self._make_key(quarter, game_time)
        self.mappings[key] = TimestampMapping(quarter, game_time, vod_seconds)
        self._save()

    def get_nearby(self, quarter: int, game_time: str, tolerance_seconds: int = 60) -> list[TimestampMapping]:
        """Get cached mappings near the target time for interpolation."""
        target_parts = game_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        nearby = []
        for mapping in self.mappings.values():
            if mapping.quarter != quarter:
                continue
            parts = mapping.game_time.split(":")
            total = int(parts[0]) * 60 + int(parts[1])
            if abs(total - target_total) <= tolerance_seconds:
                nearby.append(mapping)

        return sorted(nearby, key=lambda m: abs(
            int(m.game_time.split(":")[0]) * 60 + int(m.game_time.split(":")[1]) - target_total
        ))


class VideoIndexer:
    """Main indexer class that uses Gemini Vision to read game clocks."""

    def __init__(self, video_path: str, data_dir: Path | None = None):
        self.video_path = video_path
        self.data_dir = data_dir or Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Initialize Gemini client
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model_name = "gemini-3-flash-preview"

        # Video properties
        self._cap = None
        self._fps = None
        self._total_frames = None
        self._duration = None

    @property
    def cap(self) -> cv2.VideoCapture:
        if self._cap is None:
            self._cap = cv2.VideoCapture(self.video_path)
            if not self._cap.isOpened():
                raise ValueError(f"Could not open video: {self.video_path}")
        return self._cap

    @property
    def fps(self) -> float:
        if self._fps is None:
            self._fps = self.cap.get(cv2.CAP_PROP_FPS)
        return self._fps

    @property
    def total_frames(self) -> int:
        if self._total_frames is None:
            self._total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return self._total_frames

    @property
    def duration(self) -> float:
        """Total video duration in seconds."""
        if self._duration is None:
            self._duration = self.total_frames / self.fps
        return self._duration

    def extract_frame(self, vod_seconds: float) -> bytes:
        """Extract a frame from the video at the given VOD timestamp."""
        frame_number = int(vod_seconds * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError(f"Could not read frame at {vod_seconds}s")

        # Encode as JPEG
        _, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes()

    def read_game_clock(self, frame_bytes: bytes) -> GameClock | None:
        """Use Gemini Vision to read the game clock from a frame."""
        prompt = """Look at this NFL game broadcast frame.

Your task: Find and read the game clock display.

The game clock typically shows:
- The quarter (1st, 2nd, 3rd, 4th, or OT)
- The time remaining in the quarter (MM:SS format, counting down from 15:00)

If you can clearly see the game clock, respond with ONLY this exact format:
QUARTER: <number 1-4, or 5 for overtime>
TIME: <minutes>:<seconds>

Examples of valid responses:
QUARTER: 2
TIME: 8:34

QUARTER: 4
TIME: 0:23

If the game clock is NOT visible (commercial, replay without clock, halftime show, etc.), respond with:
NO_CLOCK_VISIBLE

Be precise. Only report what you can clearly read."""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )

        text = response.text.strip()

        if "NO_CLOCK_VISIBLE" in text:
            return None

        # Parse the response
        quarter_match = re.search(r"QUARTER:\s*(\d+)", text)
        time_match = re.search(r"TIME:\s*(\d+):(\d+)", text)

        if quarter_match and time_match:
            return GameClock(
                quarter=int(quarter_match.group(1)),
                minutes=int(time_match.group(1)),
                seconds=int(time_match.group(2))
            )

        return None

    def read_clock_at(self, vod_seconds: float, retries: int = 3, offset_step: float = 2.0) -> GameClock | None:
        """Read clock at a position, with retries at nearby frames if clock not visible."""
        offsets = [0]
        for i in range(1, retries):
            offsets.extend([i * offset_step, -i * offset_step])

        for offset in offsets:
            try_time = vod_seconds + offset
            if try_time < 0 or try_time > self.duration:
                continue

            try:
                frame = self.extract_frame(try_time)
                clock = self.read_game_clock(frame)
                if clock:
                    return clock
            except Exception as e:
                print(f"  Error reading frame at {try_time}s: {e}")
                continue

        return None

    def find_exact_time(
        self,
        target_quarter: int,
        target_time: str,
        search_start: float,
        search_end: float,
        tolerance_seconds: int = 2
    ) -> float | None:
        """
        Binary search to find exact VOD timestamp for a game time.

        Args:
            target_quarter: The quarter to find (1-4, 5 for OT)
            target_time: Game clock time to find (e.g., "8:34")
            search_start: VOD seconds to start search
            search_end: VOD seconds to end search
            tolerance_seconds: How close is "exact enough"

        Returns:
            VOD timestamp in seconds, or None if not found
        """
        target_parts = target_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        low, high = search_start, search_end
        best_match = None
        best_diff = float("inf")

        iterations = 0
        max_iterations = 20

        while high - low > 5 and iterations < max_iterations:  # 5 second precision
            iterations += 1
            mid = (low + high) / 2

            clock = self.read_clock_at(mid)
            if clock is None:
                # No clock visible, try slightly different position
                mid += 10
                clock = self.read_clock_at(mid)
                if clock is None:
                    # Still nothing, narrow search differently
                    high = mid - 10
                    continue

            print(f"  Iteration {iterations}: VOD {mid:.1f}s -> {clock}")

            # Check quarter first
            if clock.quarter != target_quarter:
                if clock.quarter < target_quarter:
                    # We're in an earlier quarter, move forward
                    low = mid
                else:
                    # We're in a later quarter, move backward
                    high = mid
                continue

            # Same quarter - compare time
            current_total = clock.total_seconds
            diff = abs(current_total - target_total)

            if diff < best_diff:
                best_diff = diff
                best_match = mid

            if diff <= tolerance_seconds:
                return mid

            # Game clock counts DOWN, so:
            # - Higher game time (e.g., 10:00) = earlier in quarter = earlier in VOD
            # - Lower game time (e.g., 2:00) = later in quarter = later in VOD
            if current_total > target_total:
                # We're at 10:00, want 8:00 -> move forward in VOD
                low = mid
            else:
                # We're at 6:00, want 8:00 -> move backward in VOD
                high = mid

        # Return best match if within reasonable tolerance
        if best_match and best_diff <= tolerance_seconds * 2:
            return best_match

        return None

    def index_quarter_manually(
        self,
        quarter: int,
        rough_start_vod: float,
        rough_end_vod: float | None = None
    ) -> QuarterBoundary:
        """
        Index a quarter given rough estimates of start/end times.
        Refines to find exact 15:00 start and 0:00 end.
        """
        print(f"\nIndexing Q{quarter}...")

        # Find exact start (15:00)
        print(f"  Finding Q{quarter} start (15:00)...")
        search_start = max(0, rough_start_vod - 120)  # 2 min before estimate
        search_end = rough_start_vod + 120  # 2 min after

        start_vod = self.find_exact_time(quarter, "15:00", search_start, search_end)
        if start_vod is None:
            print(f"  WARNING: Could not find exact Q{quarter} start, using estimate")
            start_vod = rough_start_vod
        else:
            print(f"  Found Q{quarter} start at VOD {start_vod:.1f}s")

        # Find exact end (0:00) if rough end provided
        end_vod = None
        if rough_end_vod:
            print(f"  Finding Q{quarter} end (0:00)...")
            search_start = rough_end_vod - 120
            search_end = rough_end_vod + 120

            end_vod = self.find_exact_time(quarter, "0:00", search_start, search_end, tolerance_seconds=3)
            if end_vod is None:
                print(f"  WARNING: Could not find exact Q{quarter} end, using estimate")
                end_vod = rough_end_vod
            else:
                print(f"  Found Q{quarter} end at VOD {end_vod:.1f}s")

        return QuarterBoundary(quarter=quarter, start_vod_seconds=start_vod, end_vod_seconds=end_vod)

    def create_manual_index(
        self,
        q1_start: float,
        q2_start: float,
        q3_start: float,
        q4_start: float,
        q1_end: float | None = None,
        q2_end: float | None = None,
        q3_end: float | None = None,
        q4_end: float | None = None,
        halftime_start: float | None = None,
        halftime_end: float | None = None,
    ) -> TimelineIndex:
        """
        Create a timeline index from rough manual estimates.
        Refines each quarter boundary to exact timestamps.
        """
        print(f"Creating manual index for: {self.video_path}")
        print(f"Video duration: {self.duration:.1f}s ({self.duration/60:.1f} min)")

        quarters = []

        # Index each quarter
        quarters.append(self.index_quarter_manually(1, q1_start, q1_end))
        quarters.append(self.index_quarter_manually(2, q2_start, q2_end))
        quarters.append(self.index_quarter_manually(3, q3_start, q3_end))
        quarters.append(self.index_quarter_manually(4, q4_start, q4_end))

        index = TimelineIndex(
            video_path=self.video_path,
            quarters=quarters,
            halftime_start_vod=halftime_start,
            halftime_end_vod=halftime_end,
        )

        return index

    def auto_index(self, sample_interval: int = 300) -> TimelineIndex:
        """
        Automatically discover quarter boundaries by scanning the video.

        Algorithm:
        1. Sample frames at regular intervals across the entire video
        2. Build a map of VOD time -> game clock readings
        3. Detect quarter transitions (when quarter number changes)
        4. Refine each quarter start to find exact 15:00 timestamp

        Args:
            sample_interval: Seconds between samples (default 300 = 5 minutes)
        """
        print(f"Auto-indexing: {self.video_path}")
        print(f"Video duration: {self.duration:.1f}s ({self.duration/60:.1f} min)")
        print(f"Sampling every {sample_interval}s ({sample_interval//60} min)...\n")

        # Phase 1: Coarse scan to map out the video
        samples: list[tuple[float, GameClock | None]] = []
        t = 0
        while t < self.duration:
            clock = self.read_clock_at(t, retries=2)
            samples.append((t, clock))
            status = str(clock) if clock else "NO CLOCK"
            print(f"  {t/60:6.1f} min -> {status}")
            t += sample_interval

        # Phase 2: Detect quarter boundaries from samples
        print("\n--- Analyzing samples ---")

        # Group samples by quarter
        quarter_samples: dict[int, list[tuple[float, GameClock]]] = {}
        for vod_time, clock in samples:
            if clock:
                q = clock.quarter
                if q not in quarter_samples:
                    quarter_samples[q] = []
                quarter_samples[q].append((vod_time, clock))

        print(f"Found quarters: {sorted(quarter_samples.keys())}")

        # For each quarter, find the earliest sample (rough start)
        rough_starts: dict[int, float] = {}
        for q, q_samples in quarter_samples.items():
            # Sort by game time descending (15:00 is earliest in quarter)
            q_samples_sorted = sorted(q_samples, key=lambda x: x[1].total_seconds, reverse=True)
            earliest = q_samples_sorted[0]
            rough_starts[q] = earliest[0]
            print(f"  Q{q}: earliest sample at VOD {earliest[0]/60:.1f}min (game clock {earliest[1].time_str})")

        # Phase 3: Refine each quarter to find exact 15:00
        print("\n--- Refining quarter boundaries ---")
        quarters = []

        for q in sorted(quarter_samples.keys()):
            if q > 5:  # Skip invalid quarters
                continue

            rough_start = rough_starts[q]

            # Search range: from previous sample to this sample
            # We need to search BEFORE the rough_start since 15:00 is earlier
            search_start = max(0, rough_start - sample_interval - 60)
            search_end = rough_start + 60

            print(f"\nQ{q}: Searching for 15:00 in VOD range [{search_start/60:.1f}, {search_end/60:.1f}] min")

            exact_start = self.find_exact_time(q, "15:00", search_start, search_end)

            if exact_start:
                print(f"  -> Found Q{q} start at VOD {exact_start:.1f}s ({exact_start/60:.1f} min)")
                quarters.append(QuarterBoundary(quarter=q, start_vod_seconds=exact_start))
            else:
                print(f"  -> WARNING: Could not find exact start, using rough estimate")
                quarters.append(QuarterBoundary(quarter=q, start_vod_seconds=rough_start))

        # Detect halftime (gap between Q2 and Q3)
        halftime_start = None
        halftime_end = None
        if 2 in quarter_samples and 3 in quarter_samples:
            q2_latest = max(quarter_samples[2], key=lambda x: x[0])[0]
            q3_earliest = min(quarter_samples[3], key=lambda x: x[0])[0]
            if q3_earliest - q2_latest > 300:  # More than 5 min gap = halftime
                halftime_start = q2_latest
                halftime_end = q3_earliest
                print(f"\nDetected halftime: VOD {halftime_start/60:.1f} - {halftime_end/60:.1f} min")

        index = TimelineIndex(
            video_path=self.video_path,
            quarters=sorted(quarters, key=lambda q: q.quarter),
            halftime_start_vod=halftime_start,
            halftime_end_vod=halftime_end,
        )

        print("\n=== Index Complete ===")
        for q in index.quarters:
            print(f"  Q{q.quarter}: starts at VOD {q.start_vod_seconds:.1f}s ({q.start_vod_seconds/60:.1f} min)")

        return index

    @property
    def video_basename(self) -> str:
        """Get base name of video file without extension."""
        return Path(self.video_path).stem

    def save_index(self, index: TimelineIndex, filename: str | None = None):
        """Save timeline index to JSON. Uses video-specific filename by default."""
        if filename is None:
            filename = f"{self.video_basename}_index.json"
        path = self.data_dir / filename
        with open(path, "w") as f:
            json.dump(index.to_dict(), f, indent=2)
        print(f"Saved index to {path}")

    def load_index(self, filename: str | None = None) -> TimelineIndex | None:
        """Load timeline index from JSON. Uses video-specific filename by default."""
        if filename is None:
            filename = f"{self.video_basename}_index.json"
        path = self.data_dir / filename
        if not path.exists():
            return None
        with open(path) as f:
            return TimelineIndex.from_dict(json.load(f))

    def close(self):
        """Release video capture resources."""
        if self._cap:
            self._cap.release()
            self._cap = None


def main():
    """Auto-index a video to find quarter boundaries."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m services.video_clip.indexer <video_path> [sample_interval]")
        print("\nAutomatically discovers quarter boundaries by scanning the video.")
        print("  sample_interval: seconds between samples (default: 300 = 5 min)")
        sys.exit(1)

    video_path = sys.argv[1]
    sample_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300

    indexer = VideoIndexer(video_path)

    try:
        index = indexer.auto_index(sample_interval=sample_interval)
        indexer.save_index(index)
    finally:
        indexer.close()


if __name__ == "__main__":
    main()
