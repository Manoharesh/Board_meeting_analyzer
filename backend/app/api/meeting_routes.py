"""API routes for meeting management and processing."""
from datetime import datetime
import logging
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.audio.audio_utils import decode_audio, is_silent, get_audio_duration
from app.audio.diarization import detect_speaker, get_diarizer
from app.audio.stream_handler import get_stream_handler
from app.background_worker import submit_task
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
from app.orchestration import get_meeting_orchestrator

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
        # Hardware-dependent recording/diarization disabled for recovery baseline
        # get_stream_handler().start_recording(meeting_id)
        # get_diarizer().reset()

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

        # get_stream_handler().stop_recording(meeting_id)
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
        raw_chunk = await chunk.read()
        chunk_size = len(raw_chunk)
        
        if chunk_size == 0:
            logger.warning("Received empty audio chunk for meeting %s", meeting_id)
            return {
                "status": "error",
                "message": "Empty audio payload",
                "meeting_id": meeting_id,
                "stored": False,
            }

        # Use robust decoder instead of direct buffer conversion
        audio_data = decode_audio(raw_chunk)
        
        if audio_data.size == 0:
            logger.error("Failed to decode audio chunk for meeting %s (size: %d bytes)", meeting_id, chunk_size)
            return {
                "status": "error",
                "message": "Audio decoding failed",
                "meeting_id": meeting_id,
                "stored": False,
            }

        # Check for silence (Root Mean Square check)
        if is_silent(audio_data):
            # Log with high detail to help debug sensitivity issues
            rms = np.sqrt(np.mean(np.square(audio_data)))
            logger.info("Ignoring silent chunk (RMS: %.6f) for meeting %s (bytes: %d)", 
                        rms, meeting_id, chunk_size)
            return {
                "status": "ignored",
                "message": "Silence detected",
                "meeting_id": meeting_id,
                "stored": False,
            }

        # Quick speaker detection (fast, non-blocking)
        speaker_name, confidence = detect_speaker(audio_data)
        duration = get_audio_duration(audio_data)
        
        # Submit transcription and sentiment analysis to background worker
        task_id = f"{meeting_id}_chunk_{len(get_chunks(meeting_id))}"
        submit_task(
            task_id=task_id,
            func=_process_audio_background,
            meeting_id=meeting_id,
            audio_data=audio_data,
            speaker_name=speaker_name,
        )
        
        # Store minimal chunk data immediately
        chunk_data = {
            "speaker": speaker_name,
            "speaker_name": speaker_name,
            "text": "[Processing...]",
            "timestamp": len(get_chunks(meeting_id)),
            "duration": duration,
            "sentiment": None,
            "emotion": None,
            "confidence": confidence,
            "byte_size": chunk_size
        }
        stored = store_chunk(meeting_id, chunk_data)
        
        logger.info("Accepted audio chunk: %s, bytes: %d, samples: %d, speaker: %s, duration: %.2fs", 
                    meeting_id, chunk_size, len(audio_data), speaker_name, duration)
        
        return {
            "status": "audio detected",
            "meeting_id": meeting_id,
            "stored": stored,
            "speaker": speaker_name if stored else None,
            "processing": "background",
            "duration": duration,
            "bytes_received": chunk_size
        }
    except Exception as exc:
        logger.error("Error processing audio chunk: %s", exc)
        return {
            "status": "chunk acknowledged",
            "meeting_id": meeting_id,
            "stored": False,
        }


def _process_audio_background(
    meeting_id: str,
    audio_data: np.ndarray,
    speaker_name: str,
) -> None:
    """Background task to process audio chunk."""
    try:
        orchestration_result = get_meeting_orchestrator().process_audio_chunk(audio_data, speaker_name)
        transcription = str(orchestration_result.get("transcription") or "")
        sentiment = orchestration_result.get("sentiment") or {}
        
        # Update the chunk with transcription results
        chunks = get_chunks(meeting_id)
        if chunks:
            # Find and update the most recent chunk for this speaker
            for i in range(len(chunks) - 1, -1, -1):
                if chunks[i].get("speaker") == speaker_name and chunks[i].get("text") == "[Processing...]":
                    chunks[i]["text"] = transcription or "[No speech detected]"
                    chunks[i]["sentiment"] = sentiment.get("sentiment")
                    chunks[i]["emotion"] = sentiment.get("emotion")
                    chunks[i]["confidence"] = sentiment.get("confidence")
                    
                    # Store transcript entry
                    transcript_entry = TranscriptEntry(
                        speaker_name=speaker_name,
                        speaker_id=speaker_name,
                        text=transcription,
                        timestamp=chunks[i]["timestamp"],
                        duration=chunks[i]["duration"],
                        sentiment=sentiment.get("sentiment"),
                    )
                    get_store().store_transcript_entry(meeting_id, transcript_entry)
                    break
                    
        logger.info("Completed background processing for %s", meeting_id)
    except Exception as exc:
        logger.error("Background processing error: %s", exc)


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

        sentiment = get_meeting_orchestrator().process_text_chunk(speaker_value, text_value)
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
        meeting_data = get_meeting(meeting_id)
        if not meeting_data:
            raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

        chunks = get_chunks(meeting_id)
        orchestration_payload = get_meeting_orchestrator().analyze_meeting(
            meeting_id=meeting_id,
            chunks=chunks,
            full_text=get_full_text(meeting_id),
            metadata=_meeting_context_metadata(meeting_id, meeting_data),
        )

        if not chunks:
            # Check for no_audio status for a better summary
            metadata_raw = meeting_data.get("metadata")
            status = getattr(metadata_raw, "status", None) if metadata_raw else None
            
            summary = orchestration_payload.get("summary") or ""
            if status == "no_audio":
                summary = "This meeting ended before any speech was detected, so no summary could be generated."
            
            return {
                "status": "no data",
                "meeting_id": meeting_id,
                "summary": summary,
                "key_points": [
                    str(point)
                    for point in orchestration_payload.get("key_points", [])
                    if str(point).strip()
                ],
                "decisions": [],
                "action_items": [],
                "sentiment_breakdown": orchestration_payload.get("sentiment_breakdown", {}),
                "speakers": [str(speaker) for speaker in orchestration_payload.get("speakers", [])],
            }

        decisions = [
            DecisionItem(**item)
            for item in orchestration_payload.get("decisions", [])
            if isinstance(item, dict)
        ]
        action_items = [
            ActionItem(**item)
            for item in orchestration_payload.get("action_items", [])
            if isinstance(item, dict)
        ]
        speakers = [str(speaker) for speaker in orchestration_payload.get("speakers", [])]

        analysis = MeetingAnalysis(
            meeting_id=meeting_id,
            summary=str(orchestration_payload.get("summary") or ""),
            key_points=[
                str(point)
                for point in orchestration_payload.get("key_points", [])
                if str(point).strip()
            ],
            decisions=decisions,
            action_items=action_items,
            sentiment_breakdown=orchestration_payload.get("sentiment_breakdown", {}),
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
        chunks = get_chunks(meeting_id)
        if not chunks:
            # Check if meeting was marked as no_audio
            meeting_data = get_meeting(meeting_id)
            metadata = meeting_data.get("metadata") if meeting_data else None
            
            if metadata and getattr(metadata, "status", None) == "no_audio":
                return {
                    "meeting_id": meeting_id,
                    "transcription_status": "no_audio",
                    "transcript": [{
                        "speaker": "System",
                        "text": "No audio was detected in this meeting.",
                        "timestamp": 0,
                        "sentiment": "neutral"
                    }],
                    "entry_count": 1,
                }
            
            return {
                "meeting_id": meeting_id,
                "transcription_status": "processing",
                "transcript": [],
                "entry_count": 0,
            }

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
            "transcription_status": "ready",
            "transcript": transcript,
            "entry_count": len(transcript),
        }
    except Exception as exc:
        logger.error("Error retrieving transcript: %s", exc)
        return {
            "meeting_id": meeting_id,
            "status": "error",
            "transcript": [],
            "entry_count": 0,
        }


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
            "transcription_status": getattr(metadata, "status", "unknown") if metadata else "unknown",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving meeting: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
