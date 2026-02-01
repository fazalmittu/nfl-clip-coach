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
import logging
import os
import re
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

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

        # Crop to scoreboard region (top ~12% of frame)
        frame = self._crop_scoreboard(frame)

        # Encode as JPEG
        _, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes()

    def _crop_scoreboard(self, frame):
        """Crop frame to bottom 25% where the scoreboard overlay lives."""
        h = frame.shape[0]
        return frame[int(h * 0.75):, :]

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
                logger.debug("Frame read failed at %.1fs: %s", try_time, e)
                continue

        return None

    def find_exact_time(
        self,
        target_quarter: int,
        target_time: str,
        search_start: float,
        search_end: float,
        tolerance_seconds: int = 1
    ) -> float | None:
        """
        Smart search for VOD timestamp using interpolation from readings.

        Unlike binary search, this uses each reading to calculate where
        the target SHOULD be, then jumps directly there. Much faster.
        """
        target_parts = target_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        # Collect readings as we go: [(vod_time, game_seconds), ...]
        readings: list[tuple[float, int, int]] = []  # (vod, quarter, game_secs)

        best_match = None
        best_diff = float("inf")

        # Smart starting point: use existing data to estimate, or quarter start + offset
        # Quarter starts at 15:00 (900 seconds), so offset based on target time
        quarter_start = self.index.get_quarter_start(target_quarter)
        if quarter_start:
            # Estimate: each game second ≈ 1.5 VOD seconds from quarter start
            game_elapsed = 900 - target_total  # seconds elapsed in quarter
            current_pos = quarter_start + (game_elapsed * 1.5)
            current_pos = max(search_start, min(search_end, current_pos))
        else:
            current_pos = (search_start + search_end) / 2

        iterations = 0
        max_iterations = 15

        while iterations < max_iterations:
            iterations += 1

            # Don't clamp - if math says we need to go outside range, try it
            # Just keep within video bounds
            current_pos = max(0, min(self.duration, current_pos))

            # Skip known dead zones
            if self.index.is_in_dead_zone(current_pos):
                for zone_start, zone_end in self.index.dead_zones:
                    if zone_start <= current_pos <= zone_end:
                        current_pos = zone_end + 5
                        break

            clock = self.read_clock_at(current_pos, retries=2)

            if clock is None:
                # Try nearby
                found = False
                for offset in [10, -10, 20, -20]:
                    alt = current_pos + offset
                    if 0 <= alt <= self.duration:
                        clock = self.read_clock_at(alt, retries=1)
                        if clock:
                            current_pos = alt
                            found = True
                            break
                if not found:
                    # Jump forward and try again
                    current_pos += 30
                    continue

            # Record this reading
            self.index.add_known_frame(current_pos, clock.quarter, clock.time_str)
            current_game_secs = clock.total_seconds
            readings.append((current_pos, clock.quarter, current_game_secs))

            logger.info("[iter %d/%d] VOD %.1fs → %s (target: Q%d %s)", iterations, max_iterations, current_pos, clock, target_quarter, target_time)

            # Check if we found it
            if clock.quarter == target_quarter:
                diff = abs(current_game_secs - target_total)
                if diff < best_diff:
                    best_diff = diff
                    best_match = current_pos

                if diff <= tolerance_seconds:
                    self.index.save()
                    return current_pos

            # SMART JUMP: Calculate where target should be based on this reading
            # Game time and VOD time are roughly linear (1 game sec ≈ 1-1.5 VOD sec)

            if clock.quarter == target_quarter:
                # Same quarter: interpolate directly
                # Game clock counts DOWN, so if we need higher game time, go earlier (lower VOD)
                game_diff = current_game_secs - target_total  # negative = need to go earlier in VOD
                # Estimate: 1 game second ≈ 1.3 VOD seconds (accounts for play stoppages)
                vod_jump = game_diff * 1.3
                next_pos = current_pos + vod_jump
                logger.debug("Game diff: %ds, VOD jump: %.1fs → %.1fs", game_diff, vod_jump, next_pos)
            elif clock.quarter < target_quarter:
                # We're in an earlier quarter, need to go later in VOD
                # Estimate: each quarter is ~45 min of VOD, ~15 min of game time
                quarters_diff = target_quarter - clock.quarter
                # Jump forward significantly
                next_pos = current_pos + (quarters_diff * 2000) + (900 - target_total) * 1.2
            else:
                # We're in a later quarter, need to go earlier in VOD
                quarters_diff = clock.quarter - target_quarter
                next_pos = current_pos - (quarters_diff * 2000) - (target_total) * 1.2

            # Use multiple readings to refine estimate (linear regression style)
            same_quarter_readings = [(v, g) for v, q, g in readings if q == target_quarter]
            if len(same_quarter_readings) >= 2:
                # Calculate slope: VOD change per game-second change
                r1, r2 = same_quarter_readings[-2], same_quarter_readings[-1]
                vod_diff = r2[0] - r1[0]
                game_diff = r1[1] - r2[1]  # Note: reversed because game clock counts down
                if game_diff != 0:
                    slope = vod_diff / game_diff  # VOD seconds per game second
                    # Extrapolate from most recent reading
                    game_to_target = same_quarter_readings[-1][1] - target_total
                    next_pos = same_quarter_readings[-1][0] + (game_to_target * slope)
                    logger.debug("Interpolated: slope=%.2f, jumping to %.1fs", slope, next_pos)

            # Don't oscillate - if we're close, take smaller steps
            if best_match and abs(next_pos - current_pos) > 100:
                # We're jumping far but have a close match - be more conservative
                next_pos = current_pos + (next_pos - current_pos) * 0.5

            # Detect if we're stuck (oscillating between same positions)
            if len(readings) >= 4:
                last_positions = [r[0] for r in readings[-4:]]
                unique_positions = set(round(p, 0) for p in last_positions)
                # Only converge if we have multiple UNIQUE positions that are close
                if len(unique_positions) >= 3 and max(last_positions) - min(last_positions) < 15:
                    logger.info("Converged at ~%.1fs", current_pos)
                    break
                # Also break if we're stuck on the exact same position
                if len(unique_positions) == 1:
                    logger.warning("Stuck at %.1fs, breaking out", current_pos)
                    break

            current_pos = next_pos
            logger.debug("Next position: %.1fs", current_pos)

        self.index.save()

        if best_match and best_diff <= 2:
            logger.info("Using closest match: %ds off target", best_diff)
            return best_match

        return None

    def _index_quarter(self, quarter: int, rough_start_vod: float):
        """Index a quarter given a rough estimate, saves to self.index."""
        logger.info("Indexing Q%d — searching for 15:00 near VOD %.0fs", quarter, rough_start_vod)

        search_start = max(0, rough_start_vod - 1500)
        search_end = rough_start_vod + 120

        logger.debug("Search range: [%.0fs, %.0fs]", search_start, search_end)

        start_vod = self.find_exact_time(quarter, "15:00", search_start, search_end)
        if start_vod is None:
            logger.warning("Could not find exact Q%d start, falling back to estimate %.0fs", quarter, rough_start_vod)
            start_vod = rough_start_vod
        else:
            logger.info("Q%d start found at VOD %.1fs", quarter, start_vod)

        self.index.set_quarter_start(quarter, start_vod)

    def create_manual_index(self, q1_start: float, q2_start: float, q3_start: float, q4_start: float):
        """Create index from rough manual estimates. Refines each to exact timestamps."""
        logger.info("Creating manual index for %s (%.1f min)", self.video_path, self.duration / 60)

        self._index_quarter(1, q1_start)
        self._index_quarter(2, q2_start)
        self._index_quarter(3, q3_start)
        self._index_quarter(4, q4_start)

        self.index.save()
        logger.info("Index saved to %s", self.index._cache_path)

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
        logger.info("Auto-indexing %s (%.1f min, sampling every %ds)", self.video_path, self.duration / 60, sample_interval)

        # Phase 1: Coarse scan to map out the video
        samples: list[tuple[float, GameClock | None]] = []
        t = 0
        while t < self.duration:
            clock = self.read_clock_at(t, retries=2)
            samples.append((t, clock))
            logger.info("Sample %.1f min → %s", t / 60, clock or "NO CLOCK")
            t += sample_interval

        # Phase 2: Detect quarter boundaries from samples
        quarter_samples: dict[int, list[tuple[float, GameClock]]] = {}
        for vod_time, clock in samples:
            if clock:
                q = clock.quarter
                if q not in quarter_samples:
                    quarter_samples[q] = []
                quarter_samples[q].append((vod_time, clock))

        logger.info("Detected quarters: %s", sorted(quarter_samples.keys()))

        rough_starts: dict[int, float] = {}
        for q, q_samples in quarter_samples.items():
            q_samples_sorted = sorted(q_samples, key=lambda x: x[1].total_seconds, reverse=True)
            earliest = q_samples_sorted[0]
            rough_starts[q] = earliest[0]
            logger.info("Q%d: earliest sample at VOD %.1f min (clock %s)", q, earliest[0] / 60, earliest[1].time_str)

        # Phase 3: Refine each quarter to find exact 15:00
        logger.info("Refining quarter boundaries...")

        for q in sorted(quarter_samples.keys()):
            if q > 5:  # Skip invalid quarters
                continue

            rough_start = rough_starts[q]

            # Search range: from previous sample to this sample
            # We need to search BEFORE the rough_start since 15:00 is earlier
            search_start = max(0, rough_start - sample_interval - 60)
            search_end = rough_start + 60

            logger.debug("Q%d: searching 15:00 in VOD [%.1f, %.1f] min", q, search_start / 60, search_end / 60)

            exact_start = self.find_exact_time(q, "15:00", search_start, search_end)

            if exact_start:
                logger.info("Q%d start → VOD %.1fs (%.1f min)", q, exact_start, exact_start / 60)
                self.index.set_quarter_start(q, exact_start)
            else:
                logger.warning("Q%d: exact start not found, using rough estimate %.0fs", q, rough_start)
                self.index.set_quarter_start(q, rough_start)

        self.index.save()

        for q, vod_secs in sorted(self.index.quarters.items()):
            logger.info("Q%d starts at VOD %.1fs (%.1f min)", q, vod_secs, vod_secs / 60)
        logger.info("Index saved to %s", self.index._cache_path)

    def find_vod_timestamp(self, quarter: int, game_time: str) -> float:
        """Find the VOD timestamp for a specific game time."""
        if not self.index.is_indexed:
            raise ValueError("No index found. Run auto_index first.")

        quarter_range = self.index.get_quarter_range(quarter)
        if not quarter_range:
            raise ValueError(f"Quarter {quarter} not found in index")

        base_start, base_end = quarter_range
        target_parts = game_time.split(":")
        target_total = int(target_parts[0]) * 60 + int(target_parts[1])

        # Check cache
        cached = self.index.get_mapping(quarter, game_time)
        if cached:
            logger.info("Cache hit: Q%d %s → VOD %.1fs", quarter, game_time, cached)
            return cached

        # Smart search using interpolation
        logger.info("Searching for Q%d %s in VOD range [%.0fs, %.0fs]", quarter, game_time, base_start, base_end)

        vod_timestamp = self.find_exact_time(quarter, game_time, base_start, base_end)

        if vod_timestamp:
            self.index.set_mapping(quarter, game_time, vod_timestamp)
            logger.info("Found and cached: Q%d %s → VOD %.1fs", quarter, game_time, vod_timestamp)
            return vod_timestamp

        raise RuntimeError(f"Could not find Q{quarter} {game_time} in quarter range")


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
