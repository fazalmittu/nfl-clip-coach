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


class VideoIndex:
    """
    Combined index for a video containing:
    - Quarter boundaries (Q1-Q4 start times)
    - Cached timestamp mappings (game time -> VOD time)
    - Known frame readings (VOD time -> game clock)
    - Dead zones (VOD ranges with no game clock - ads, halftime, etc.)
    """

    def __init__(self, video_path: str, cache_dir: Path):
        self.video_path = video_path
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Quarter start times: {1: 90.0, 2: 1571.25, ...}
        self.quarters: dict[int, float] = {}
        # Cached mappings: {"Q2_8:34": 2397.15, ...}
        self.mappings: dict[str, float] = {}
        # Known frame readings: {"1800.5": {"quarter": 2, "time": "13:45"}, ...}
        self.known_frames: dict[str, dict] = {}
        # Dead zones (no game clock visible): [[start, end], ...]
        self.dead_zones: list[list[float]] = []

        self._load()

    @property
    def _cache_path(self) -> Path:
        video_name = Path(self.video_path).stem
        return self.cache_dir / f"{video_name}.json"

    def _load(self):
        if self._cache_path.exists():
            with open(self._cache_path) as f:
                data = json.load(f)
                self.quarters = {int(k): v for k, v in data.get("quarters", {}).items()}
                self.mappings = data.get("mappings", {})
                self.known_frames = data.get("known_frames", {})
                self.dead_zones = data.get("dead_zones", [])

    def save(self):
        with open(self._cache_path, "w") as f:
            json.dump({
                "video_path": self.video_path,
                "quarters": self.quarters,
                "mappings": self.mappings,
                "known_frames": self.known_frames,
                "dead_zones": self.dead_zones,
            }, f, indent=2)

    def add_known_frame(self, vod_seconds: float, quarter: int, game_time: str):
        """Record a successful frame reading."""
        self.known_frames[str(round(vod_seconds, 1))] = {
            "quarter": quarter,
            "time": game_time
        }

    def add_dead_zone(self, start: float, end: float):
        """Record a VOD range with no game clock."""
        # Merge with existing zones if overlapping
        new_zone = [start, end]
        merged = []
        for zone in self.dead_zones:
            if zone[1] < new_zone[0] - 10 or zone[0] > new_zone[1] + 10:
                # No overlap
                merged.append(zone)
            else:
                # Merge
                new_zone = [min(zone[0], new_zone[0]), max(zone[1], new_zone[1])]
        merged.append(new_zone)
        self.dead_zones = sorted(merged, key=lambda z: z[0])

    def is_in_dead_zone(self, vod_seconds: float) -> bool:
        """Check if a VOD timestamp is in a known dead zone."""
        for start, end in self.dead_zones:
            if start <= vod_seconds <= end:
                return True
        return False

    def get_nearest_known_frame(self, vod_seconds: float) -> tuple[float, dict] | None:
        """Find the nearest known frame reading to a VOD timestamp."""
        if not self.known_frames:
            return None
        nearest = min(self.known_frames.keys(), key=lambda k: abs(float(k) - vod_seconds))
        return (float(nearest), self.known_frames[nearest])

    @property
    def is_indexed(self) -> bool:
        return len(self.quarters) > 0

    def set_quarter_start(self, quarter: int, vod_seconds: float):
        self.quarters[quarter] = vod_seconds

    def get_quarter_start(self, quarter: int) -> float | None:
        return self.quarters.get(quarter)

    def get_quarter_range(self, quarter: int) -> tuple[float, float] | None:
        """Get VOD time range for a quarter (start to next quarter's start)."""
        if quarter not in self.quarters:
            return None

        start = self.quarters[quarter]
        sorted_quarters = sorted(self.quarters.keys())
        idx = sorted_quarters.index(quarter)

        if idx + 1 < len(sorted_quarters):
            end = self.quarters[sorted_quarters[idx + 1]]
        else:
            end = start + 2700  # 45 min fallback for last quarter

        return (start, end)

    def _make_key(self, quarter: int, game_time: str) -> str:
        return f"Q{quarter}_{game_time}"

    def get_mapping(self, quarter: int, game_time: str) -> float | None:
        return self.mappings.get(self._make_key(quarter, game_time))

    def set_mapping(self, quarter: int, game_time: str, vod_seconds: float):
        self.mappings[self._make_key(quarter, game_time)] = vod_seconds
        self.save()

    def get_nearby_mappings(self, quarter: int, game_time: str, tolerance_seconds: int = 60) -> list[tuple[str, float]]:
        """Get cached mappings near the target time for interpolation."""
        target_parts = game_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        nearby = []
        prefix = f"Q{quarter}_"
        for key, vod_secs in self.mappings.items():
            if not key.startswith(prefix):
                continue
            cached_time = key[len(prefix):]
            parts = cached_time.split(":")
            total = int(parts[0]) * 60 + int(parts[1])
            if abs(total - target_total) <= tolerance_seconds:
                nearby.append((cached_time, vod_secs))

        return sorted(nearby, key=lambda x: abs(
            int(x[0].split(":")[0]) * 60 + int(x[0].split(":")[1]) - target_total
        ))


class VideoIndexer:
    """Main indexer class that uses Gemini Vision to read game clocks."""

    def __init__(self, video_path: str, data_dir: Path | None = None):
        self.video_path = video_path

        # Cache directory (not committed to git)
        self.cache_dir = Path(__file__).parent.parent.parent / ".cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Combined index + cache
        self.index = VideoIndex(video_path, self.cache_dir)

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
        tolerance_seconds: int = 3
    ) -> float | None:
        """
        Search for exact VOD timestamp for a game time.
        Records all frame readings to the index for future searches.
        """
        target_parts = target_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        low, high = search_start, search_end
        best_match = None
        best_diff = float("inf")
        no_clock_streak = []  # Track consecutive no-clock positions

        iterations = 0
        max_iterations = 25

        while high - low > 3 and iterations < max_iterations:
            iterations += 1
            mid = (low + high) / 2

            # Skip known dead zones
            if self.index.is_in_dead_zone(mid):
                # Jump past the dead zone
                for zone_start, zone_end in self.index.dead_zones:
                    if zone_start <= mid <= zone_end:
                        mid = zone_end + 5
                        break

            clock = self.read_clock_at(mid)

            if clock is None:
                no_clock_streak.append(mid)
                # Try nearby positions
                for offset in [15, -15, 30, -30]:
                    alt_pos = mid + offset
                    if search_start <= alt_pos <= search_end and not self.index.is_in_dead_zone(alt_pos):
                        clock = self.read_clock_at(alt_pos)
                        if clock:
                            mid = alt_pos
                            no_clock_streak = []
                            break

                if clock is None:
                    # Record potential dead zone if we have multiple consecutive failures
                    if len(no_clock_streak) >= 2:
                        zone_start = min(no_clock_streak) - 10
                        zone_end = max(no_clock_streak) + 10
                        self.index.add_dead_zone(zone_start, zone_end)
                        print(f"  Recorded dead zone: {zone_start:.0f}s - {zone_end:.0f}s")
                    # Move search window
                    high = mid - 20
                    continue

            # Record successful frame reading
            self.index.add_known_frame(mid, clock.quarter, clock.time_str)
            print(f"  Iteration {iterations}: VOD {mid:.1f}s -> {clock}")

            # Check quarter first
            if clock.quarter != target_quarter:
                if clock.quarter < target_quarter:
                    low = mid
                else:
                    high = mid
                continue

            # Same quarter - compare time
            current_total = clock.total_seconds
            diff = abs(current_total - target_total)

            if diff < best_diff:
                best_diff = diff
                best_match = mid

            if diff <= tolerance_seconds:
                self.index.save()
                return mid

            # Game clock counts DOWN, so:
            # - Higher game time (e.g., 10:00) = earlier in quarter = earlier in VOD
            # - Lower game time (e.g., 2:00) = later in quarter = later in VOD
            if current_total > target_total:
                low = mid
            else:
                high = mid

        # Save what we learned
        self.index.save()

        # Return best match if within reasonable tolerance (5 seconds)
        if best_match and best_diff <= 5:
            print(f"  Using closest match: {best_diff:.0f}s off")
            return best_match

        return None

    def _index_quarter(self, quarter: int, rough_start_vod: float):
        """Index a quarter given a rough estimate, saves to self.index."""
        print(f"\nIndexing Q{quarter}...")
        print(f"  Finding Q{quarter} start (15:00)...")

        search_start = max(0, rough_start_vod - 120)
        search_end = rough_start_vod + 120

        start_vod = self.find_exact_time(quarter, "15:00", search_start, search_end)
        if start_vod is None:
            print(f"  WARNING: Could not find exact Q{quarter} start, using estimate")
            start_vod = rough_start_vod
        else:
            print(f"  Found Q{quarter} start at VOD {start_vod:.1f}s")

        self.index.set_quarter_start(quarter, start_vod)

    def create_manual_index(self, q1_start: float, q2_start: float, q3_start: float, q4_start: float):
        """Create index from rough manual estimates. Refines each to exact timestamps."""
        print(f"Creating manual index for: {self.video_path}")
        print(f"Video duration: {self.duration:.1f}s ({self.duration/60:.1f} min)")

        self._index_quarter(1, q1_start)
        self._index_quarter(2, q2_start)
        self._index_quarter(3, q3_start)
        self._index_quarter(4, q4_start)

        self.index.save()
        print(f"\nSaved to {self.index._cache_path}")

    def auto_index(self, sample_interval: int = 300):
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
                self.index.set_quarter_start(q, exact_start)
            else:
                print(f"  -> WARNING: Could not find exact start, using rough estimate")
                self.index.set_quarter_start(q, rough_start)

        self.index.save()

        print("\n=== Index Complete ===")
        for q, vod_secs in sorted(self.index.quarters.items()):
            print(f"  Q{q}: starts at VOD {vod_secs:.1f}s ({vod_secs/60:.1f} min)")
        print(f"Saved to {self.index._cache_path}")

    def find_vod_timestamp(self, quarter: int, game_time: str, max_retries: int = 3) -> float:
        """
        Find the VOD timestamp for a specific game time.
        Retries with wider search ranges until found.
        """
        # Check cache first
        cached = self.index.get_mapping(quarter, game_time)
        if cached:
            print(f"Cache hit: Q{quarter} {game_time} -> {cached:.1f}s")
            return cached

        # Check index exists
        if not self.index.is_indexed:
            raise ValueError("No index found. Run auto_index first.")

        quarter_range = self.index.get_quarter_range(quarter)
        if not quarter_range:
            raise ValueError(f"Quarter {quarter} not found in index")

        base_start, base_end = quarter_range
        target_parts = game_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        for attempt in range(max_retries):
            search_start, search_end = base_start, base_end

            # Use nearby cached mappings to narrow search
            nearby = self.index.get_nearby_mappings(quarter, game_time, tolerance_seconds=120 + attempt * 60)
            if nearby:
                for cached_time, vod_secs in nearby:
                    m_parts = cached_time.split(":")
                    m_total = int(m_parts[0]) * 60 + int(m_parts[1])
                    time_diff = m_total - target_total
                    estimated_vod = vod_secs - (time_diff * 1.5)
                    # Widen range on each retry
                    buffer = 120 + attempt * 60
                    search_start = max(base_start, estimated_vod - buffer)
                    search_end = min(base_end, estimated_vod + buffer)

            # Also use known frames for better estimation
            if self.index.known_frames:
                for vod_str, frame_info in self.index.known_frames.items():
                    if frame_info["quarter"] == quarter:
                        f_parts = frame_info["time"].split(":")
                        f_total = int(f_parts[0]) * 60 + int(f_parts[1])
                        time_diff = f_total - target_total
                        estimated = float(vod_str) - (time_diff * 1.3)
                        if base_start <= estimated <= base_end:
                            buffer = 90 + attempt * 45
                            search_start = max(search_start, estimated - buffer)
                            search_end = min(search_end, estimated + buffer)
                            break

            if attempt > 0:
                print(f"\nRetry {attempt + 1}/{max_retries} with range [{search_start:.0f}s, {search_end:.0f}s]")
            else:
                print(f"Searching for Q{quarter} {game_time} in VOD range [{search_start:.0f}s, {search_end:.0f}s]")

            vod_timestamp = self.find_exact_time(quarter, game_time, search_start, search_end)

            if vod_timestamp:
                self.index.set_mapping(quarter, game_time, vod_timestamp)
                print(f"Found and cached: Q{quarter} {game_time} -> {vod_timestamp:.1f}s")
                return vod_timestamp

            # Widen search for next attempt
            print(f"  Not found in range, will retry with wider search...")

        # Final fallback - search entire quarter
        print(f"\nFinal attempt: searching entire quarter range [{base_start:.0f}s, {base_end:.0f}s]")
        vod_timestamp = self.find_exact_time(quarter, game_time, base_start, base_end, tolerance_seconds=5)

        if vod_timestamp:
            self.index.set_mapping(quarter, game_time, vod_timestamp)
            print(f"Found and cached: Q{quarter} {game_time} -> {vod_timestamp:.1f}s")
            return vod_timestamp

        raise RuntimeError(f"Could not find Q{quarter} {game_time} after exhaustive search")

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
        indexer.auto_index(sample_interval=sample_interval)
    finally:
        indexer.close()


if __name__ == "__main__":
    main()
