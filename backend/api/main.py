from dotenv import load_dotenv
load_dotenv()

import logging
import sys

from fastapi import FastAPI, Query

from models.schemas import DataQueryResult, ClipResponse
from services.data_query import query as data_query
from services.video_clip import get_clips

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Default video path (49ers vs Lions 2023 NFC Championship)
DEFAULT_VIDEO = "data/49ers-Lions.mp4"


@app.get("/")
def hello_world():
    return {"message": "hello world"}


@app.get("/query", response_model=DataQueryResult)
def query_plays(q: str = Query(..., description="Natural-language query for NFL plays")):
    logger.info(f"Query: {q}")
    result = data_query(q)
    logger.info(f"Found {len(result.timestamps)} plays")
    return result


@app.get("/clips", response_model=ClipResponse)
def get_video_clips(q: str = Query(..., description="Natural-language query for NFL plays")):
    """
    Query plays and return video clip timestamps.
    """
    logger.info(f"=== Clips request: '{q}' ===")

    # Step 1: Get game timestamps from data query
    logger.info("Step 1: Querying play-by-play data...")
    result = data_query(q)
    logger.info(f"Found {len(result.timestamps)} matching plays")

    if not result.timestamps:
        logger.info("No plays found, returning empty response")
        return ClipResponse(clips=[])

    # Log what we found
    for i, ts in enumerate(result.timestamps[:5]):  # Show first 5
        logger.info(f"  Play {i+1}: Q{ts.quarter} {ts.time} ({ts.duration_seconds:.0f}s)")
    if len(result.timestamps) > 5:
        logger.info(f"  ... and {len(result.timestamps) - 5} more")

    # Step 2: Convert to video clip timestamps
    logger.info("Step 2: Converting to VOD timestamps...")
    clips = get_clips(DEFAULT_VIDEO, result.timestamps)
    logger.info(f"Generated {len(clips)} clips")

    logger.info("=== Done ===")
    return ClipResponse(clips=clips)
