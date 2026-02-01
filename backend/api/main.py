from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models.schemas import DataQueryResult, ClipResponse
from services.data_query import query as data_query
from services.video_clip import get_clips

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


@app.get("/query", response_model=DataQueryResult)
def query_plays(q: str = Query(..., description="Natural-language query for NFL plays")):
    return data_query(q)


@app.get("/clips", response_model=ClipResponse)
def get_video_clips(q: str = Query(..., description="Natural-language query for NFL plays")):
    result = data_query(q)
    if not result.timestamps:
        return ClipResponse(clips=[])
    clips = get_clips(DEFAULT_VIDEO, result.timestamps)
    return ClipResponse(clips=clips)


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
