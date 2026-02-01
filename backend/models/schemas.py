from pydantic import BaseModel


class GameTimestamp(BaseModel):
    quarter: int  # 1-4, 5 for OT
    time: str  # "12:45" (game clock, counts down)
    play_data: dict | None = None  # raw play-by-play row data


class ClipTimestamp(BaseModel):
    start_time: float  # seconds into the video
    end_time: float | None = None  # end of clip (for loop / display)
    video_path: str  # path to source video
    description: str | None = None  # full play description text
    play_type: str | None = None
    down: int | None = None
    ydstogo: int | None = None
    yards_gained: int | None = None
    posteam: str | None = None
    defteam: str | None = None
    quarter: int | None = None
    game_time: str | None = None
    posteam_score: int | None = None
    defteam_score: int | None = None
    passer: str | None = None
    rusher: str | None = None
    receiver: str | None = None
    is_touchdown: bool = False
    is_interception: bool = False
    is_sack: bool = False
    is_fumble: bool = False
    yardline_100: int | None = None
    wpa: float | None = None


class DataQueryResult(BaseModel):
    timestamps: list[GameTimestamp]


class ClipResponse(BaseModel):
    clips: list[ClipTimestamp]


class AnalyzeRequest(BaseModel):
    mode: str  # "chat" | "video"
    query: str
    session_id: str | None = None
    play_buffer_seconds: float | None = None  # extra seconds after play (video mode)
    game_name: str | None = None  # selected game from frontend, e.g. "49ers vs Lions - 2023 NFC Championship"


class AnalyzeResponse(BaseModel):
    mode: str
    response: str | None = None
    clips: list[ClipTimestamp] | None = None
    suggest_clips: bool = False  # when True, frontend shows "Find clips" CTA for this query
