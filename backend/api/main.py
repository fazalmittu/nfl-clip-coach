from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query

from models.schemas import DataQueryResult
from services.data_query import query as data_query

app = FastAPI()


@app.get("/")
def hello_world():
    return {"message": "hello world"}


@app.get("/query", response_model=DataQueryResult)
def query_plays(q: str = Query(..., description="Natural-language query for NFL plays")):
    return data_query(q)
