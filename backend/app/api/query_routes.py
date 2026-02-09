"""API routes for querying meeting content."""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from app.memory.meeting_store import get_chunks, get_store
from app.ai.topic_query import query_by_topic, semantic_query
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)
router = APIRouter()


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
        chunks = get_chunks(meeting_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
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
        
    except Exception as e:
        logger.error(f"Error querying by topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic/{meeting_id}")
def semantic_query_endpoint(meeting_id: str, query: str) -> dict:
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
        chunks = get_chunks(meeting_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Get semantic results
        relevant_chunks, answer = semantic_query(chunks, query)
        
        return {
            "meeting_id": meeting_id,
            "query": query,
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
        
    except Exception as e:
        logger.error(f"Error in semantic query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/{meeting_id}")
def ask_meeting_endpoint(meeting_id: str, question: str) -> dict:
    """
    Ask a question about the meeting using conversational AI.
    
    Args:
        meeting_id: ID of the meeting
        question: Question about the meeting
        
    Returns:
        AI-generated answer with supporting evidence
    """
    try:
        store = get_store()
        chunks = get_chunks(meeting_id)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Build context from chunks
        context_text = "\n".join([
            f"{c.get('speaker', 'Unknown')}: {c.get('text', '')}"
            for c in chunks[:20]  # Limit to prevent token overflow
        ])
        
        system = "You are a helpful assistant analyzing board meetings. Answer questions based on the provided transcript."
        
        prompt = f"""
Meeting Transcript:
{context_text}

Question: {question}

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
            "question": question,
            "answer": answer,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(status_code=404, detail="Meeting not found")
        
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
        
    except Exception as e:
        logger.error(f"Error getting speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
