from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.clip_search import query as clip_search_query
from services.video_clip import get_clips
from services.game_analyst import chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data", StaticFiles(directory="data"), name="data")

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
            buffer = req.play_buffer_seconds if req.play_buffer_seconds is not None else 15.0
            clips = get_clips(DEFAULT_VIDEO, result.timestamps, play_buffer_seconds=buffer)
        return AnalyzeResponse(mode="video", clips=clips)

    elif req.mode == "chat":
        session_id = req.session_id or "default"
        response = chat(session_id, req.query, game_context=req.game_name)

        # Only suggest clips for play-specific queries, not general analysis
        suggest_clips = False
        query_lower = req.query.lower().strip()
        general_keywords = [
            "summarize", "summary", "overview", "recap", "analyze", "analysis",
            "how did", "who won", "what happened", "tell me about", "explain",
            "what was the score", "final score",
        ]
        is_general = any(kw in query_lower for kw in general_keywords)

        if not is_general:
            try:
                clip_result = clip_search_query(req.query)
                if clip_result.timestamps:
                    suggest_clips = True
            except Exception:
                pass

        return AnalyzeResponse(mode="chat", response=response, suggest_clips=suggest_clips)

    return AnalyzeResponse(mode=req.mode, response="Unknown mode. Use 'chat' or 'video'.")


@app.post("/index")
def index_video(clear_cache: bool = Query(False, description="Clear existing cache before indexing")):
    """Index the video to find quarter boundaries."""
    from services.video_clip import VideoIndexer

    indexer = VideoIndexer(DEFAULT_VIDEO)

    if clear_cache:
        print("Clearing all cached data...")
        indexer.index.quarters = {}
        indexer.index.mappings = {}
        indexer.index.known_frames = {}
        indexer.index.dead_zones = []
        indexer.index.save()

    # Re-index if no quarters found (cleared or never indexed)
    if not indexer.index.is_indexed:
        print("Running auto-index to find quarter boundaries...")
        indexer.auto_index()

    result = {
        "video": DEFAULT_VIDEO,
        "quarters": indexer.index.quarters,
        "cached_mappings": len(indexer.index.mappings),
        "known_frames": len(indexer.index.known_frames)
    }

    indexer.close()
    return result
