import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.meeting_routes import router as meeting_router
from app.api.query_routes import router as query_router
from app.api.voice_routes import router as voice_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Board Meeting Analyzer",
    version="2.0.0",
    description="Intelligent board meeting transcription, analysis, and Q&A system"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(meeting_router, prefix="/api/meeting", tags=["Meeting Management"])
app.include_router(query_router, prefix="/api/query", tags=["Meeting Queries"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice Enrollment"])

@app.get("/")
def root():
    return {
        "status": "AI Board Meeting Analyzer running",
        "version": "2.0.0",
        "endpoints": {
            "meetings": "/api/meeting",
            "queries": "/api/query",
            "voice_enrollment": "/api/voice"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Board Meeting Analyzer"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
