"""API routes for querying meeting content."""
from typing import Optional
import logging

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.memory.meeting_store import get_chunks, get_meeting
from app.ai.topic_query import query_by_topic, semantic_query
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)
router = APIRouter()


class SemanticQueryRequest(BaseModel):
    query: str = Field(min_length=1)


class AskMeetingRequest(BaseModel):
    question: str = Field(min_length=1)


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
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        chunks = get_chunks(meeting_id)
        
        results = query_by_topic(chunks, topic)
        
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
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        query_value = (payload.query if payload else query or "").strip()
        if not query_value:
            raise HTTPException(status_code=400, detail="query is required")

        chunks = get_chunks(meeting_id)
        if not chunks:
            return {
                "meeting_id": meeting_id,
                "query": query_value,
                "answer": "No transcript data available yet.",
                "relevant_chunks": [],
                "chunk_count": 0
            }
        
        # Get semantic results
        relevant_chunks, answer = semantic_query(chunks, query_value)
        
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
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        question_value = (payload.question if payload else question or "").strip()
        if not question_value:
            raise HTTPException(status_code=400, detail="question is required")

        chunks = get_chunks(meeting_id)
        
        if not chunks:
            return {
                "meeting_id": meeting_id,
                "question": question_value,
                "answer": "No transcript data available yet.",
                "status": "no_data"
            }
        
        # Build context from chunks
        context_text = "\n".join([
            f"{c.get('speaker', 'Unknown')}: {c.get('text', '')}"
            for c in chunks[:20]  # Limit to prevent token overflow
        ])
        
        system = "You are a helpful assistant analyzing board meetings. Answer questions based on the provided transcript."
        
        prompt = f"""
Meeting Transcript:
{context_text}

Question: {question_value}

Provide a concise, factual answer based on the meeting transcript.
"""
        
        result = call_llm(prompt, system)
        
        # Extract answer
        if isinstance(result, dict):
            answer = result.get('answer', str(result))
        else:
            answer = str(result)
        
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
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

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
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting speakers: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
