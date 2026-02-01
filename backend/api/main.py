from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.clip_search import query as clip_search_query
from services.video_clip import get_clips
from services.game_analyst import chat

app = FastAPI()

DEFAULT_VIDEO = "data/49ers-Lions.mp4"


@app.get("/")
def hello_world():
    return {"message": "hello world"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if req.mode == "video":
        result = clip_search_query(req.query)
        clips = []
        if result.timestamps:
            clips = get_clips(DEFAULT_VIDEO, result.timestamps)
        return AnalyzeResponse(mode="video", clips=clips)

    elif req.mode == "chat":
        session_id = req.session_id or "default"
        response = chat(session_id, req.query)
        return AnalyzeResponse(mode="chat", response=response)

    return AnalyzeResponse(mode=req.mode, response="Unknown mode. Use 'chat' or 'video'.")
