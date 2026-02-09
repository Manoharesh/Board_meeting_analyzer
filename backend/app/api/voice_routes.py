"""API routes for speaker voice enrollment and management."""
from fastapi import APIRouter, HTTPException, File, UploadFile
from typing import Optional, List
import logging
import numpy as np

from app.audio.voice_enroll import (
    get_enrollment_manager,
    enroll_voice,
    get_all_enrolled_speakers
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/enroll")
async def enroll_speaker_endpoint(
    speaker_name: str,
    audio_file: UploadFile = File(...)
) -> dict:
    """
    Enroll a speaker by uploading a 10-20 second voice sample.
    
    Args:
        speaker_name: Name of the speaker
        audio_file: Audio file (WAV, MP3, etc.)
        
    Returns:
        Enrollment result with success status
    """
    try:
        if not speaker_name or not speaker_name.strip():
            raise HTTPException(status_code=400, detail="Speaker name required")
        
        # Read audio file
        audio_data = await audio_file.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data provided")
        
        # Convert to numpy array
        # Assuming 16-bit PCM audio at 16kHz
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Enroll speaker
        success, message = enroll_voice(speaker_name, audio_array)
        
        if success:
            logger.info(f"Successfully enrolled speaker: {speaker_name}")
            return {
                "status": "success",
                "message": message,
                "speaker_name": speaker_name,
                "audio_duration": len(audio_array) / 16000
            }
        else:
            logger.warning(f"Failed to enroll speaker {speaker_name}: {message}")
            raise HTTPException(status_code=400, detail=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling speaker: {e}")
        raise HTTPException(status_code=500, detail=f"Error enrolling speaker: {str(e)}")


@router.get("/speakers")
def get_enrolled_speakers() -> dict:
    """
    Get list of all enrolled speakers.
    
    Returns:
        List of enrolled speakers with enrollment timestamps
    """
    try:
        manager = get_enrollment_manager()
        speakers = manager.get_enrolled_speakers()
        
        return {
            "status": "success",
            "speaker_count": len(speakers),
            "speakers": [
                {
                    "name": name,
                    "enrolled_at": info['enrolled_time'],
                    "audio_duration": info['audio_length'] / 16000
                }
                for name, info in speakers.items()
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting enrolled speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speakers/{speaker_name}")
def get_speaker_info(speaker_name: str) -> dict:
    """
    Get information about an enrolled speaker.
    
    Args:
        speaker_name: Name of the speaker
        
    Returns:
        Speaker enrollment information
    """
    try:
        manager = get_enrollment_manager()
        
        if not manager.is_speaker_enrolled(speaker_name):
            raise HTTPException(status_code=404, detail=f"Speaker {speaker_name} not enrolled")
        
        speakers = manager.get_enrolled_speakers()
        if speaker_name in speakers:
            info = speakers[speaker_name]
            return {
                "status": "success",
                "speaker_name": speaker_name,
                "enrolled_at": info['enrolled_time'],
                "audio_duration": info['audio_length'] / 16000
            }
        
        raise HTTPException(status_code=404, detail="Speaker not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting speaker info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/speakers/{speaker_name}")
def remove_speaker(speaker_name: str) -> dict:
    """
    Remove an enrolled speaker.
    
    Args:
        speaker_name: Name of the speaker to remove
        
    Returns:
        Removal status
    """
    try:
        manager = get_enrollment_manager()
        success, message = manager.remove_speaker(speaker_name)
        
        if success:
            logger.info(f"Removed speaker: {speaker_name}")
            return {
                "status": "success",
                "message": message
            }
        else:
            raise HTTPException(status_code=404, detail=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speakers/{speaker_name}/re-enroll")
async def reenroll_speaker(
    speaker_name: str,
    audio_file: UploadFile = File(...)
) -> dict:
    """
    Re-enroll a speaker with a new voice sample.
    
    Args:
        speaker_name: Name of the speaker
        audio_file: New audio file
        
    Returns:
        Re-enrollment result
    """
    try:
        manager = get_enrollment_manager()
        
        if not manager.is_speaker_enrolled(speaker_name):
            raise HTTPException(status_code=404, detail=f"Speaker {speaker_name} not enrolled")
        
        # Read audio file
        audio_data = await audio_file.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data provided")
        
        # Convert to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Remove old enrollment and enroll new
        manager.remove_speaker(speaker_name)
        success, message = enroll_voice(speaker_name, audio_array)
        
        if success:
            logger.info(f"Re-enrolled speaker: {speaker_name}")
            return {
                "status": "success",
                "message": message,
                "speaker_name": speaker_name,
                "audio_duration": len(audio_array) / 16000
            }
        else:
            raise HTTPException(status_code=400, detail=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-enrolling speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
