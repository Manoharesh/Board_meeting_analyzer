"""API routes for meeting management and processing."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional, List
import logging
import io
import numpy as np
from datetime import datetime

from app.memory.meeting_store import (
    create_meeting, end_meeting, store_chunk, get_meeting, 
    get_chunks, get_full_text, get_store
)
from app.audio.stream_handler import get_stream_handler
from app.audio.diarization import detect_speaker, get_diarizer
from app.transcription.realtime_stt import transcribe_audio
from app.ai.summarizer import summarize
from app.ai.decision_extractor import extract_decisions
from app.ai.action_items import extract_action_items
from app.ai.sentiment import track_speaker_sentiment, get_sentiment_breakdown
from app.models.schemas import MeetingMetadata, MeetingAnalysis, TranscriptEntry, DecisionItem, ActionItem, AudioChunk

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/start")
def start_meeting(
    meeting_name: str,
    participants: Optional[List[str]] = None
) -> dict:
    """
    Start a new meeting.
    
    Args:
        meeting_name: Name of the meeting
        participants: List of participant names (optional)
        
    Returns:
        Meeting metadata with meeting_id
    """
    try:
        # Generate meeting ID from timestamp and name
        meeting_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{meeting_name.replace(' ', '_')}"
        
        metadata = create_meeting(meeting_id, meeting_name, participants or [])
        
        # Start audio streaming
        stream_handler = get_stream_handler()
        stream_handler.start_recording()
        
        # Reset diarizer for new meeting
        diarizer = get_diarizer()
        diarizer.reset()
        
        logger.info(f"Started meeting: {meeting_id}")
        
        return {
            "status": "meeting started",
            "meeting_id": meeting_id,
            "meeting_name": meeting_name,
            "start_time": metadata.start_time.isoformat(),
            "participants": metadata.participants
        }
        
    except Exception as e:
        logger.error(f"Error starting meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end/{meeting_id}")
def end_meeting_endpoint(meeting_id: str) -> dict:
    """
    End a meeting and return final data.
    
    Args:
        meeting_id: ID of the meeting to end
        
    Returns:
        Meeting data and analysis
    """
    try:
        # Stop recording
        stream_handler = get_stream_handler()
        
        # Get meeting data
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
        
        # End the meeting
        end_meeting(meeting_id)
        
        logger.info(f"Ended meeting: {meeting_id}")
        
        return {
            "status": "meeting ended",
            "meeting_id": meeting_id,
            "chunk_count": len(meeting_data.get('chunks', [])),
            "end_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error ending meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio-chunk/{meeting_id}")
def add_audio_chunk(meeting_id: str, chunk: bytes = File(...)) -> dict:
    """
    Process and store an audio chunk.
    Handles speaker diarization, transcription, and sentiment analysis.
    
    Args:
        meeting_id: ID of the meeting
        chunk: Audio chunk as bytes
        
    Returns:
        Processing result with speaker ID and transcription
    """
    try:
        # Get meeting
        meeting = get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
        
        # Convert bytes to numpy array
        audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Detect speaker
        speaker_name, confidence = detect_speaker(audio_data)
        
        # Transcribe audio
        success, transcription = transcribe_audio(audio_data)
        
        if not success or not transcription:
            logger.warning(f"Failed to transcribe chunk for meeting {meeting_id}")
            transcription = "[Transcription failed]"
        
        # Analyze sentiment
        sentiment = track_speaker_sentiment(speaker_name, transcription)
        
        # Store in meeting
        chunk_data = {
            "speaker": speaker_name,
            "speaker_name": speaker_name,
            "text": transcription,
            "timestamp": len(get_chunks(meeting_id)),  # Sequential timestamp
            "duration": len(audio_data) / 16000,
            "sentiment": sentiment.get('sentiment'),
            "emotion": sentiment.get('emotion'),
            "confidence": sentiment.get('confidence')
        }
        
        store_chunk(meeting_id, chunk_data)
        
        # Store transcript entry
        transcript_entry = TranscriptEntry(
            speaker_name=speaker_name,
            speaker_id=speaker_name,
            text=transcription,
            timestamp=chunk_data['timestamp'],
            duration=chunk_data['duration'],
            sentiment=sentiment.get('sentiment')
        )
        
        store = get_store()
        store.store_transcript_entry(meeting_id, transcript_entry)
        
        logger.info(f"Processed audio chunk for {meeting_id}: {speaker_name}")
        
        return {
            "status": "chunk processed",
            "speaker": speaker_name,
            "confidence": confidence,
            "transcription": transcription[:100] + "..." if len(transcription) > 100 else transcription,
            "sentiment": sentiment.get('sentiment'),
            "emotion": sentiment.get('emotion')
        }
        
    except Exception as e:
        logger.error(f"Error processing audio chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunk")
def add_chunk(meeting_id: str, speaker: str, text: str) -> dict:
    """
    Add a text chunk directly (alternative to audio).
    
    Args:
        meeting_id: ID of the meeting
        speaker: Speaker name
        text: Transcribed text
        
    Returns:
        Chunk storage result
    """
    try:
        chunk = {"speaker": speaker, "text": text, "timestamp": len(get_chunks(meeting_id))}
        store_chunk(meeting_id, chunk)
        
        # Analyze sentiment
        sentiment = track_speaker_sentiment(speaker, text)
        
        logger.info(f"Stored text chunk for {meeting_id}: {speaker}")
        
        return {
            "status": "chunk stored",
            "speaker": speaker,
            "sentiment": sentiment.get('sentiment')
        }
        
    except Exception as e:
        logger.error(f"Error adding chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{meeting_id}")
def analyze_meeting(meeting_id: str) -> dict:
    """
    Generate comprehensive meeting analysis.
    Includes summary, decisions, action items, and sentiment breakdown.
    
    Args:
        meeting_id: ID of the meeting to analyze
        
    Returns:
        Complete meeting analysis
    """
    try:
        chunks = get_chunks(meeting_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="No chunks found for meeting")
        
        full_text = get_full_text(meeting_id)
        
        # Generate summary
        summary_result = summarize(chunks)
        if isinstance(summary_result, dict):
            summary = summary_result.get('summary', '')
            key_points = summary_result.get('key_points', [])
        else:
            summary = str(summary_result)
            key_points = []
        
        # Extract decisions and action items
        decisions_raw = extract_decisions(full_text)
        decisions = [
            DecisionItem(
                id=d.get('id'),
                description=d.get('description'),
                owner=d.get('owner'),
                status=d.get('status', 'open')
            )
            for d in decisions_raw
        ]
        
        action_items_raw = extract_action_items(full_text)
        action_items = [
            ActionItem(
                id=a.get('id'),
                description=a.get('description'),
                owner=a.get('owner'),
                due_date=a.get('due_date'),
                priority=a.get('priority', 'medium')
            )
            for a in action_items_raw
        ]
        
        # Get sentiment breakdown
        sentiment_data = get_sentiment_breakdown()
        
        # Get unique speakers
        speakers = list(set(c.get('speaker', 'Unknown') for c in chunks))
        
        analysis = MeetingAnalysis(
            meeting_id=meeting_id,
            summary=summary,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            sentiment_breakdown=sentiment_data,
            speakers=speakers
        )
        
        # Store analysis
        store = get_store()
        store.store_analysis(meeting_id, analysis)
        
        logger.info(f"Completed analysis for meeting: {meeting_id}")
        
        return {
            "status": "analysis complete",
            "meeting_id": meeting_id,
            "summary": summary,
            "key_points": key_points,
            "decisions": [d.dict() for d in decisions],
            "action_items": [a.dict() for a in action_items],
            "sentiment_breakdown": sentiment_data,
            "speakers": speakers
        }
        
    except Exception as e:
        logger.error(f"Error analyzing meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcript/{meeting_id}")
def get_transcript(meeting_id: str) -> dict:
    """
    Get the complete transcript for a meeting.
    
    Args:
        meeting_id: ID of the meeting
        
    Returns:
        Meeting transcript with speaker names
    """
    try:
        chunks = get_chunks(meeting_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="No transcript found")
        
        transcript = []
        for chunk in chunks:
            transcript.append({
                "speaker": chunk.get('speaker', 'Unknown'),
                "text": chunk.get('text', ''),
                "timestamp": chunk.get('timestamp', 0),
                "sentiment": chunk.get('sentiment')
            })
        
        return {
            "meeting_id": meeting_id,
            "transcript": transcript,
            "entry_count": len(transcript)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}")
def get_meeting_data(meeting_id: str) -> dict:
    """
    Get complete meeting data.
    
    Args:
        meeting_id: ID of the meeting
        
    Returns:
        All meeting data including metadata, transcript, and analysis
    """
    try:
        store = get_store()
        meeting = store.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
        
        metadata = store.get_meeting_metadata(meeting_id)
        transcript = store.get_meeting_transcript(meeting_id)
        analysis = store.get_analysis(meeting_id)
        
        return {
            "meeting_id": meeting_id,
            "metadata": metadata.dict() if metadata else {},
            "transcript_entries": len(transcript),
            "has_analysis": analysis is not None,
            "chunk_count": len(store.get_meeting_chunks(meeting_id))
        }
        
    except Exception as e:
        logger.error(f"Error retrieving meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/list/all")
def list_meetings() -> dict:
    """
    List all meetings.
    
    Returns:
        List of all meetings with basic information
    """
    try:
        store = get_store()
        meetings = store.list_meetings()
        
        return {
            "status": "success",
            "count": len(meetings),
            "meetings": meetings
        }
        
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
