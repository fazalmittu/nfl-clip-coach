from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query

from models.schemas import DataQueryResult, ClipResponse
from services.data_query import query as data_query
from services.video_clip import get_clips

app = FastAPI()

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
