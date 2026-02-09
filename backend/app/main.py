import sys
from pathlib import Path
from fastapi import FastAPI
from app.api.meeting_routes import router as meeting_router
from app.api.query_routes import router as query_router

app = FastAPI(
    title="AI Board Meeting Analyzer",
    version="1.0.0"
)

app.include_router(meeting_router, prefix="/meeting", tags=["Meeting"])
app.include_router(query_router, prefix="/query", tags=["Query"])

@app.get("/")
def root():
    return {"status": "AI Board Meeting Analyzer running"}
