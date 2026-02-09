"""API routes for meeting management and processing."""
from datetime import datetime
import logging
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.ai.action_items import extract_action_items
from app.ai.decision_extractor import extract_decisions
from app.ai.sentiment import get_sentiment_breakdown, track_speaker_sentiment
from app.ai.summarizer import summarize
from app.audio.diarization import detect_speaker, get_diarizer
from app.audio.stream_handler import get_stream_handler
from app.memory.meeting_store import (
    create_meeting,
    end_meeting,
    get_chunks,
    get_full_text,
    get_meeting,
    get_store,
    store_chunk,
)
from app.models.schemas import ActionItem, DecisionItem, MeetingAnalysis, TranscriptEntry
from app.transcription.realtime_stt import transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter()


class StartMeetingRequest(BaseModel):
    meeting_name: str = Field(..., min_length=1)
    participants: List[str] = Field(default_factory=list)


class TextChunkRequest(BaseModel):
    meeting_id: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)


def _clean_participants(participants: Optional[List[str]]) -> List[str]:
    if not participants:
        return []
    return [name.strip() for name in participants if name and name.strip()]


@router.post("/start")
def start_meeting(
    payload: StartMeetingRequest = Body(...),
) -> dict:
    """Start a new meeting."""
    try:
        meeting_name_value = payload.meeting_name.strip()
        participants_value = _clean_participants(payload.participants)

        if not meeting_name_value:
            raise HTTPException(status_code=400, detail="meeting_name is required")

        safe_name = "_".join(meeting_name_value.split()) or "meeting"
        meeting_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"

        metadata = create_meeting(meeting_id, meeting_name_value, participants_value)
        get_stream_handler().start_recording()
        get_diarizer().reset()

        logger.info("Started meeting: %s", meeting_id)
        return {
            "status": "meeting started",
            "meeting_id": meeting_id,
            "meeting_name": metadata.meeting_name,
            "start_time": metadata.start_time.isoformat(),
            "participants": metadata.participants,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error starting meeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/end/{meeting_id}")
def end_meeting_endpoint(meeting_id: str) -> dict:
    """End an active meeting."""
    try:
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        get_stream_handler().stop_recording()
        if not end_meeting(meeting_id):
            raise HTTPException(status_code=500, detail=f"Failed to end meeting {meeting_id}")

        logger.info("Ended meeting: %s", meeting_id)
        return {
            "status": "meeting ended",
            "meeting_id": meeting_id,
            "chunk_count": len(meeting_data.get("chunks", [])),
            "end_time": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error ending meeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/audio-chunk/{meeting_id}")
async def add_audio_chunk(meeting_id: str, chunk: UploadFile = File(...)) -> dict:
    """Process and store an uploaded audio chunk."""
    try:
        meeting = get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        raw_chunk = await chunk.read()
        if not raw_chunk:
            raise HTTPException(status_code=400, detail="Audio chunk is empty")

        audio_data = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        if audio_data.size == 0:
            raise HTTPException(status_code=400, detail="Audio chunk contains no valid samples")

        speaker_name, confidence = detect_speaker(audio_data)
        success, transcription = transcribe_audio(audio_data)

        if not success or not transcription:
            logger.warning("Failed to transcribe chunk for meeting %s", meeting_id)
            transcription = "[Transcription failed]"

        sentiment = track_speaker_sentiment(speaker_name, transcription)
        chunk_data = {
            "speaker": speaker_name,
            "speaker_name": speaker_name,
            "text": transcription,
            "timestamp": len(get_chunks(meeting_id)),
            "duration": len(audio_data) / 16000,
            "sentiment": sentiment.get("sentiment"),
            "emotion": sentiment.get("emotion"),
            "confidence": sentiment.get("confidence"),
        }

        store_chunk(meeting_id, chunk_data)

        transcript_entry = TranscriptEntry(
            speaker_name=speaker_name,
            speaker_id=speaker_name,
            text=transcription,
            timestamp=chunk_data["timestamp"],
            duration=chunk_data["duration"],
            sentiment=sentiment.get("sentiment"),
        )
        get_store().store_transcript_entry(meeting_id, transcript_entry)

        logger.info("Processed audio chunk for %s (%s)", meeting_id, speaker_name)
        return {
            "status": "chunk processed",
            "speaker": speaker_name,
            "confidence": confidence,
            "transcription": transcription[:100] + "..." if len(transcription) > 100 else transcription,
            "sentiment": sentiment.get("sentiment"),
            "emotion": sentiment.get("emotion"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing audio chunk: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chunk")
def add_chunk(
    payload: Optional[TextChunkRequest] = Body(default=None),
    meeting_id: Optional[str] = None,
    speaker: Optional[str] = None,
    text: Optional[str] = None,
) -> dict:
    """Add a text chunk directly (without audio upload)."""
    try:
        meeting_id_value = (payload.meeting_id if payload else meeting_id or "").strip()
        speaker_value = (payload.speaker if payload else speaker or "").strip()
        text_value = (payload.text if payload else text or "").strip()

        if not meeting_id_value:
            raise HTTPException(status_code=400, detail="meeting_id is required")
        if not speaker_value:
            raise HTTPException(status_code=400, detail="speaker is required")
        if not text_value:
            raise HTTPException(status_code=400, detail="text is required")

        if not get_meeting(meeting_id_value):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id_value} not found")

        chunk_data = {
            "speaker": speaker_value,
            "text": text_value,
            "timestamp": len(get_chunks(meeting_id_value)),
        }
        store_chunk(meeting_id_value, chunk_data)

        sentiment = track_speaker_sentiment(speaker_value, text_value)
        transcript_entry = TranscriptEntry(
            speaker_name=speaker_value,
            speaker_id=speaker_value,
            text=text_value,
            timestamp=chunk_data["timestamp"],
            duration=0.0,
            sentiment=sentiment.get("sentiment"),
        )
        get_store().store_transcript_entry(meeting_id_value, transcript_entry)

        logger.info("Stored text chunk for %s (%s)", meeting_id_value, speaker_value)
        return {
            "status": "chunk stored",
            "meeting_id": meeting_id_value,
            "speaker": speaker_value,
            "sentiment": sentiment.get("sentiment"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error adding chunk: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analysis/{meeting_id}")
def analyze_meeting(meeting_id: str) -> dict:
    """Generate summary, decisions, action items, and sentiment metrics."""
    try:
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        chunks = get_chunks(meeting_id)
        if not chunks:
            return {
                "status": "no data",
                "meeting_id": meeting_id,
                "summary": "",
                "key_points": [],
                "decisions": [],
                "action_items": [],
                "sentiment_breakdown": {},
                "speakers": [],
            }

        summary_result = summarize(chunks)
        summary = ""
        key_points: List[str] = []
        if isinstance(summary_result, dict):
            summary = str(summary_result.get("summary") or "")
            raw_key_points = summary_result.get("key_points") or []
            if isinstance(raw_key_points, list):
                key_points = [str(point) for point in raw_key_points if point]
        elif summary_result:
            summary = str(summary_result)

        full_text = get_full_text(meeting_id)
        decisions = [DecisionItem(**item) for item in extract_decisions(full_text)]
        action_items = [ActionItem(**item) for item in extract_action_items(full_text)]
        sentiment_data = get_sentiment_breakdown()
        speakers = sorted({chunk.get("speaker", "Unknown") for chunk in chunks})

        analysis = MeetingAnalysis(
            meeting_id=meeting_id,
            summary=summary,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            sentiment_breakdown=sentiment_data,
            speakers=speakers,
        )
        get_store().store_analysis(meeting_id, analysis)

        logger.info("Completed analysis for meeting: %s", meeting_id)
        return {
            "status": "analysis complete",
            **analysis.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error analyzing meeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/transcript/{meeting_id}")
def get_transcript(meeting_id: str) -> dict:
    """Get a meeting transcript in UI-friendly format."""
    try:
        if not get_meeting(meeting_id):
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        chunks = get_chunks(meeting_id)
        transcript = [
            {
                "speaker": chunk.get("speaker", "Unknown"),
                "text": chunk.get("text", ""),
                "timestamp": chunk.get("timestamp", 0),
                "sentiment": chunk.get("sentiment"),
            }
            for chunk in chunks
        ]

        return {
            "meeting_id": meeting_id,
            "transcript": transcript,
            "entry_count": len(transcript),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving transcript: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/meetings/list/all")
def list_meetings() -> dict:
    """List all meetings with summary metadata."""
    try:
        meetings = get_store().list_meetings()
        return {
            "status": "success",
            "count": len(meetings),
            "meetings": meetings,
        }
    except Exception as exc:
        logger.error("Error listing meetings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{meeting_id}")
def get_meeting_data(meeting_id: str) -> dict:
    """Get metadata and high-level state for a single meeting."""
    try:
        store = get_store()
        meeting = store.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        metadata = store.get_meeting_metadata(meeting_id)
        analysis = store.get_analysis(meeting_id)
        chunk_count = len(store.get_meeting_chunks(meeting_id))

        return {
            "meeting_id": meeting_id,
            "metadata": metadata.model_dump() if metadata else {},
            "transcript_entries": chunk_count,
            "has_analysis": analysis is not None,
            "chunk_count": chunk_count,
            "analysis": analysis.model_dump() if analysis else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving meeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
