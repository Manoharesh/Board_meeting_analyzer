"""
Speaker diarization module.
Uses speaker embeddings and voice registered speakers to identify speakers.
"""
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class SpeakerDiarizer:
    """Implements speaker diarization and identification."""
    
    def __init__(self):
        self.speaker_embeddings: Dict[str, np.ndarray] = {}
        self.speaker_counter = 0
        self.unknown_speakers: Dict[int, str] = {}  # Maps anonymous speaker IDs to speaker identities
        
    def register_speaker_embedding(self, speaker_name: str, embedding: np.ndarray):
        """Register a speaker with their voice embedding."""
        self.speaker_embeddings[speaker_name] = embedding
        logger.info(f"Registered speaker: {speaker_name}")
        
    def detect_speaker(self, audio_chunk: np.ndarray, speaker_embeddings: Optional[Dict] = None) -> Tuple[str, float]:
        """
        Detect speaker from audio chunk using embeddings.
        Returns (speaker_name, confidence_score).
        """
        try:
            # Extract embedding from audio (placeholder - would use actual model)
            chunk_embedding = self._extract_embedding(audio_chunk)
            
            if speaker_embeddings is None:
                speaker_embeddings = self.speaker_embeddings
                
            if not speaker_embeddings:
                # No registered speakers, assign generic ID
                speaker_id = self.speaker_counter
                self.speaker_counter += 1
                self.unknown_speakers[speaker_id] = f"Speaker_{speaker_id + 1}"
                return f"Speaker_{speaker_id + 1}", 0.0
            
            # Find closest matching speaker
            best_match = None
            best_distance = float('inf')
            
            for speaker_name, registered_embedding in speaker_embeddings.items():
                distance = self._cosine_distance(chunk_embedding, registered_embedding)
                if distance < best_distance:
                    best_distance = distance
                    best_match = speaker_name
            
            # If match is below confidence threshold, treat as unknown speaker
            confidence = max(0, 1 - best_distance)
            
            if confidence < 0.5:  # Threshold
                speaker_id = self.speaker_counter
                self.speaker_counter += 1
                self.unknown_speakers[speaker_id] = f"Speaker_{speaker_id + 1}"
                logger.debug(f"Low confidence match. Assigned: Speaker_{speaker_id + 1}")
                return f"Speaker_{speaker_id + 1}", confidence
            
            logger.debug(f"Matched speaker: {best_match} with confidence: {confidence}")
            return best_match, confidence
            
        except Exception as e:
            logger.error(f"Error detecting speaker: {e}")
            speaker_id = self.speaker_counter
            self.speaker_counter += 1
            return f"Speaker_{speaker_id + 1}", 0.0
    
    def _extract_embedding(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Extract speaker embedding from audio.
        This is a simplified version - in production, use pyannote.audio or similar.
        """
        # Simple feature extraction for demo: MFCC-like features
        if len(audio_chunk) == 0:
            return np.zeros(128)
            
        # Compute simple spectral features
        embedding = np.zeros(128)
        try:
            # Compute energy, zero crossing rate, etc.
            embedding[0] = np.mean(np.abs(audio_chunk))  # RMS energy
            embedding[1] = np.sum(np.abs(np.diff(audio_chunk))) / len(audio_chunk)  # Zero-crossing rate
            
            # Expand to full embedding
            for i in range(2, 128):
                embedding[i] = np.random.randn() * 0.01 + embedding[0]
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            
        return embedding / (np.linalg.norm(embedding) + 1e-8)  # Normalize
    
    def _cosine_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine distance between two vectors."""
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
        return 1 - np.dot(vec1_norm, vec2_norm)
    
    def reset(self):
        """Reset speaker counter for new meeting."""
        self.speaker_counter = 0
        self.unknown_speakers.clear()


# Global diarizer instance
_diarizer = SpeakerDiarizer()


def get_diarizer() -> SpeakerDiarizer:
    """Get the global diarizer instance."""
    return _diarizer


def detect_speaker(audio_chunk: np.ndarray, speaker_embeddings: Optional[Dict] = None) -> Tuple[str, float]:
    """Detect speaker from audio chunk."""
    diarizer = get_diarizer()
    return diarizer.detect_speaker(audio_chunk, speaker_embeddings)


def register_speaker(speaker_name: str, embedding: np.ndarray):
    """Register a speaker embedding."""
    diarizer = get_diarizer()
    diarizer.register_speaker_embedding(speaker_name, embedding)
