"""
Handles incoming real-time audio streams from microphone.
Uses WebSocket or HTTP multipart for streaming audio chunks.
"""
import io
import logging
from typing import Generator, Optional
import numpy as np

logger = logging.getLogger(__name__)

class AudioStreamHandler:
    """Manages audio stream reception and buffering."""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_buffer = []
        self.is_recording = False
        
    def start_recording(self):
        """Start recording audio stream."""
        self.is_recording = True
        self.audio_buffer = []
        logger.info("Audio recording started")
        
    def stop_recording(self) -> bytes:
        """Stop recording and return the full audio buffer."""
        self.is_recording = False
        audio_data = np.concatenate(self.audio_buffer) if self.audio_buffer else np.array([])
        logger.info(f"Audio recording stopped. Total samples: {len(audio_data)}")
        return audio_data.astype(np.int16).tobytes()
    
    def process_audio_chunk(self, chunk: bytes) -> None:
        """Process incoming audio chunk."""
        if not self.is_recording:
            return
            
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            self.audio_buffer.append(audio_array)
            logger.debug(f"Processed audio chunk: {len(audio_array)} samples")
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            
    def get_buffered_audio(self) -> Optional[np.ndarray]:
        """Get the current buffered audio as numpy array."""
        if not self.audio_buffer:
            return None
        return np.concatenate(self.audio_buffer)
    
    def clear_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer = []
        logger.debug("Audio buffer cleared")


# Global stream handler instance
_stream_handler = AudioStreamHandler()


def get_stream_handler() -> AudioStreamHandler:
    """Get the global stream handler instance."""
    return _stream_handler


def receive_audio_chunk(chunk: bytes) -> dict:
    """Handle incoming audio chunk from client."""
    handler = get_stream_handler()
    handler.process_audio_chunk(chunk)
    return {"status": "chunk received", "size": len(chunk)}
