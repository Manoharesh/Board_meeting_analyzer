"""API routes for querying meeting content."""
from typing import Optional
import logging

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.memory.meeting_store import get_chunks, get_meeting
from app.orchestration import get_meeting_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


class SemanticQueryRequest(BaseModel):
    query: Optional[str] = None


class AskMeetingRequest(BaseModel):
    question: Optional[str] = None


def _meeting_context_metadata(meeting_id: str, meeting_data: Optional[dict]) -> dict:
    metadata_payload = {"meeting_id": meeting_id}
    if not isinstance(meeting_data, dict):
        return metadata_payload

    raw_metadata = meeting_data.get("metadata")
    if raw_metadata is None:
        return metadata_payload

    meeting_name = getattr(raw_metadata, "meeting_name", None)
    start_time = getattr(raw_metadata, "start_time", None)
    participants = getattr(raw_metadata, "participants", None)

    if meeting_name:
        metadata_payload["meeting_name"] = meeting_name
    if start_time is not None:
        metadata_payload["start_time"] = start_time
    if participants:
        metadata_payload["participants"] = participants

    return metadata_payload


@router.get("/topic/{meeting_id}")
def topic_query_endpoint(meeting_id: str, topic: str) -> dict:
    """
    Query meeting for content related to a specific topic.
    Uses keyword matching to find relevant segments.
    
    Args:
        meeting_id: ID of the meeting
        topic: Topic to search for
        
    Returns:
        List of relevant meeting segments
    """
    try:
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        chunks = get_chunks(meeting_id)
        
        results = get_meeting_orchestrator().query_topic(chunks, topic)
        
        return {
            "meeting_id": meeting_id,
            "topic": topic,
            "results_count": len(results),
            "results": [
                {
                    "speaker": r.get('speaker', 'Unknown'),
                    "text": r.get('text', ''),
                    "timestamp": r.get('timestamp', 0),
                    "sentiment": r.get('sentiment')
                }
                for r in results
            ]
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error querying by topic: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/semantic/{meeting_id}")
def semantic_query_endpoint(
    meeting_id: str,
    payload: Optional[SemanticQueryRequest] = Body(default=None),
    query: Optional[str] = None,
) -> dict:
    """
    Perform semantic search on meeting content using natural language.
    Uses LLM to understand questions and provide answers.
    
    Args:
        meeting_id: ID of the meeting
        query: Natural language question
        
    Returns:
        Answer with relevant segments from the meeting
    """
    try:
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        query_value = ((payload.query if payload else query) or "").strip()

        chunks = get_chunks(meeting_id)
        if not chunks:
            return {
                "meeting_id": meeting_id,
                "query": query_value,
                "answer": "No transcript yet. You can still ask questions.",
                "relevant_chunks": [],
                "chunk_count": 0
            }
        
        relevant_chunks, answer = get_meeting_orchestrator().semantic_query(
            meeting_id=meeting_id,
            chunks=chunks,
            query=query_value,
            metadata=_meeting_context_metadata(meeting_id, meeting_data),
        )
        
        return {
            "meeting_id": meeting_id,
            "query": query_value,
            "answer": answer,
            "relevant_chunks": [
                {
                    "speaker": c.get('speaker', 'Unknown'),
                    "text": c.get('text', ''),
                    "timestamp": c.get('timestamp', 0)
                }
                for c in relevant_chunks
            ],
            "chunk_count": len(relevant_chunks)
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in semantic query: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ask/{meeting_id}")
def ask_meeting_endpoint(
    meeting_id: str,
    payload: Optional[AskMeetingRequest] = Body(default=None),
    question: Optional[str] = None,
) -> dict:
    """
    Ask a question about the meeting using conversational AI.
    
    Args:
        meeting_id: ID of the meeting
        question: Question about the meeting
        
    Returns:
        AI-generated answer with supporting evidence
    """
    try:
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        question_value = ((payload.question if payload else question) or "").strip()

        chunks = get_chunks(meeting_id)
        
        if not chunks:
            return {
                "meeting_id": meeting_id,
                "question": question_value,
                "answer": "No transcript yet. You can still ask questions.",
                "status": "no_data"
            }
        
        answer = get_meeting_orchestrator().ask_question(
            meeting_id=meeting_id,
            chunks=chunks,
            question=question_value,
            metadata=_meeting_context_metadata(meeting_id, meeting_data),
        )
        
        return {
            "meeting_id": meeting_id,
            "question": question_value,
            "answer": answer,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error answering question: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/speakers/{meeting_id}")
def get_speakers_endpoint(meeting_id: str) -> dict:
    """
    Get list of speakers in a meeting.
    
    Args:
        meeting_id: ID of the meeting
        
    Returns:
        List of unique speakers and their contribution count
    """
    try:
        chunks = get_chunks(meeting_id)
        if not chunks:
            return {
                "meeting_id": meeting_id,
                "speaker_count": 0,
                "speakers": []
            }
        
        speaker_stats = {}
        for chunk in chunks:
            speaker = chunk.get('speaker', 'Unknown')
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'count': 0,
                    'sentiments': {}
                }
            speaker_stats[speaker]['count'] += 1
            
            sentiment = chunk.get('sentiment', 'neutral')
            speaker_stats[speaker]['sentiments'][sentiment] = speaker_stats[speaker]['sentiments'].get(sentiment, 0) + 1
        
        return {
            "meeting_id": meeting_id,
            "speaker_count": len(speaker_stats),
            "speakers": [
                {
                    "name": name,
                    "contributions": stats['count'],
                    "sentiment_breakdown": stats['sentiments']
                }
                for name, stats in speaker_stats.items()
            ]
        }
        
    except Exception as exc:
        logger.error("Error getting speakers: %s", exc)
        return {
            "meeting_id": meeting_id,
            "speaker_count": 0,
            "speakers": []
        }
