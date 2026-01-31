from pydantic import BaseModel


class GameTimestamp(BaseModel):
    quarter: int  # 1-4, 5 for OT
    time: str  # "12:45" (game clock, counts down)


class ClipTimestamp(BaseModel):
    start_time: float  # seconds into the video
    end_time: float  # seconds into the video
    video_path: str  # path to source video
    description: str | None = None  # formation analysis, play summary


class DataQueryResult(BaseModel):
    timestamps: list[GameTimestamp]


class ClipResponse(BaseModel):
    clips: list[ClipTimestamp]
