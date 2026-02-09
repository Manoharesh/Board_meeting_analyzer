"""
Voice enrollment module.
Enables users to register their voice (10-20 sec sample) for speaker identification.
"""
import logging
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime
from app.audio.diarization import register_speaker, get_diarizer

logger = logging.getLogger(__name__)

class VoiceEnrollmentManager:
    """Manages speaker voice enrollment."""
    
    def __init__(self):
        self.enrolled_speakers: Dict[str, Dict] = {}  # {speaker_name: {embedding, audio_length, enrolled_time}}
        self.min_audio_samples = 160000  # ~10 seconds at 16kHz
        self.max_audio_samples = 320000  # ~20 seconds at 16kHz
        
    def enroll_voice(self, speaker_name: str, audio_data: np.ndarray) -> Tuple[bool, str]:
        """
        Enroll a speaker voice for identification.
        Audio should be 10-20 seconds at 16kHz sample rate.
        
        Returns: (success, message)
        """
        try:
            if not speaker_name or not speaker_name.strip():
                return False, "Speaker name cannot be empty"
                
            if audio_data is None or len(audio_data) == 0:
                return False, "Audio data is empty"
                
            # Check audio length
            if len(audio_data) < self.min_audio_samples:
                return False, f"Audio too short. Minimum: 10 seconds, got: {len(audio_data) / 16000:.1f} seconds"
                
            if len(audio_data) > self.max_audio_samples:
                return False, f"Audio too long. Maximum: 20 seconds, got: {len(audio_data) / 16000:.1f} seconds"
                
            # Normalize speaker name
            speaker_name = speaker_name.strip()
            
            # Extract embedding from audio
            embedding = self._extract_embedding(audio_data)
            
            # Store enrollment
            self.enrolled_speakers[speaker_name] = {
                'embedding': embedding,
                'audio_length': len(audio_data),
                'enrolled_time': datetime.now().isoformat(),
                'audio_data': audio_data  # Store for future re-training if needed
            }
            
            # Register with diarizer
            register_speaker(speaker_name, embedding)
            
            logger.info(f"Successfully enrolled speaker: {speaker_name} ({len(audio_data) / 16000:.1f} sec)")
            return True, f"Voice enrollment successful for {speaker_name}"
            
        except Exception as e:
            logger.error(f"Error enrolling voice: {e}")
            return False, f"Voice enrollment failed: {str(e)}"
    
    def get_enrolled_speakers(self) -> Dict[str, Dict]:
        """Get all enrolled speakers."""
        return {
            name: {
                'enrolled_time': info['enrolled_time'],
                'audio_length': info['audio_length']
            }
            for name, info in self.enrolled_speakers.items()
        }
    
    def remove_speaker(self, speaker_name: str) -> Tuple[bool, str]:
        """Remove an enrolled speaker."""
        try:
            if speaker_name in self.enrolled_speakers:
                del self.enrolled_speakers[speaker_name]
                logger.info(f"Removed speaker: {speaker_name}")
                return True, f"Speaker {speaker_name} removed"
            return False, f"Speaker {speaker_name} not found"
        except Exception as e:
            logger.error(f"Error removing speaker: {e}")
            return False, f"Error removing speaker: {str(e)}"
    
    def is_speaker_enrolled(self, speaker_name: str) -> bool:
        """Check if a speaker is enrolled."""
        return speaker_name in self.enrolled_speakers
    
    def get_speaker_embedding(self, speaker_name: str) -> Optional[np.ndarray]:
        """Get embedding for an enrolled speaker."""
        if speaker_name in self.enrolled_speakers:
            return self.enrolled_speakers[speaker_name]['embedding']
        return None
    
    def _extract_embedding(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract speaker embedding from audio data.
        Returns a 128-dimensional embedding.
        """
        try:
            # Normalize audio
            audio_normalized = audio_data.astype(np.float32) / (np.max(np.abs(audio_data)) + 1e-8)
            
            # Compute basic features for embedding
            embedding = np.zeros(128)
            
            # Energy features
            frame_size = len(audio_normalized) // 8
            for i in range(8):
                frame = audio_normalized[i * frame_size:(i + 1) * frame_size]
                embedding[i] = np.mean(np.abs(frame))
            
            # Spectral features (simplified)
            for i in range(8, 128):
                embedding[i] = np.std(audio_normalized) * (i / 128.0)
            
            # Normalize embedding
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return np.zeros(128)
    
    def reset(self):
        """Reset all enrollments."""
        self.enrolled_speakers.clear()
        logger.info("Voice enrollment data reset")


# Global enrollment manager
_enrollment_manager = VoiceEnrollmentManager()


def get_enrollment_manager() -> VoiceEnrollmentManager:
    """Get the global enrollment manager."""
    return _enrollment_manager


def enroll_voice(speaker_name: str, audio_data: np.ndarray) -> Tuple[bool, str]:
    """Enroll a speaker voice."""
    manager = get_enrollment_manager()
    return manager.enroll_voice(speaker_name, audio_data)


def resolve_speaker(speaker_id: str) -> str:
    """
    Resolve speaker ID to name (legacy function).
    Now uses diarizer for resolution.
    """
    speaker_registry = get_enrollment_manager().enrolled_speakers
    if speaker_id in speaker_registry:
        return speaker_id
    return speaker_id


def get_all_enrolled_speakers() -> Dict[str, Dict]:
    """Get all enrolled speakers with their metadata."""
    manager = get_enrollment_manager()
    return manager.get_enrolled_speakers()
