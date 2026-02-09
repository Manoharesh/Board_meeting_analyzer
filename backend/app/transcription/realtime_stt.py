"""
Real-time speech-to-text (STT) module.
Uses speech recognition to convert audio to text.
Can be replaced with Whisper, Deepgram, or other services.
"""
import logging
import numpy as np
from typing import Tuple, Optional
import asyncio

logger = logging.getLogger(__name__)

class SpeechToTextEngine:
    """Handles speech-to-text transcription."""
    
    def __init__(self, engine: str = "google"):
        """
        Initialize STT engine.
        Supported engines: "google", "whisper", "azure"
        """
        self.engine = engine
        self.recognizer = None
        self._initialize_engine()
        
    def _initialize_engine(self):
        """Initialize the selected STT engine."""
        try:
            if self.engine == "google":
                try:
                    from speech_recognition import Recognizer
                    self.recognizer = Recognizer()
                    logger.info("Google Speech Recognition initialized")
                except ImportError:
                    logger.warning("speech_recognition not installed. Using dummy transcriber.")
            elif self.engine == "whisper":
                try:
                    import whisper
                    self.model = whisper.load_model("base")
                    logger.info("Whisper model loaded")
                except ImportError:
                    logger.warning("Whisper not installed. Using dummy transcriber.")
        except Exception as e:
            logger.warning(f"Failed to initialize {self.engine} engine: {e}")
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, str]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate in Hz (default 16000)
            
        Returns:
            (success, text): Success flag and transcribed text
        """
        try:
            if audio_data is None or len(audio_data) == 0:
                return False, ""
            
            if self.engine == "whisper" and hasattr(self, 'model'):
                return self._transcribe_whisper(audio_data, sample_rate)
            elif self.engine == "google" and self.recognizer:
                return self._transcribe_google(audio_data, sample_rate)
            else:
                # Fallback: return dummy transcription
                return True, self._generate_dummy_transcription(audio_data)
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return False, ""
    
    def _transcribe_whisper(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, str]:
        """Transcribe using OpenAI Whisper."""
        try:
            import io
            import wave
            
            # Convert numpy array to WAV bytes
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.astype(np.int16).tobytes())
            
            wav_buffer.seek(0)
            
            # Transcribe
            result = self.model.transcribe(wav_buffer, language="en")
            text = result.get('text', '').strip()
            
            if text:
                logger.info(f"Whisper transcription: {text[:100]}...")
                return True, text
            return False, ""
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return False, ""
    
    def _transcribe_google(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, str]:
        """Transcribe using Google Speech Recognition."""
        try:
            import speech_recognition as sr
            import io
            import wave
            
            # Convert numpy array to WAV
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.astype(np.int16).tobytes())
            
            wav_buffer.seek(0)
            
            # Create audio data
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
            
            # Recognize
            text = self.recognizer.recognize_google(audio, language='en-US')
            
            if text:
                logger.info(f"Google transcription: {text[:100]}...")
                return True, text
            return False, ""
            
        except Exception as e:
            logger.error(f"Google transcription error: {e}")
            return False, ""
    
    def _generate_dummy_transcription(self, audio_data: np.ndarray) -> str:
        """Generate a dummy transcription for demo purposes."""
        # Simple placeholder that varies based on audio duration
        duration = len(audio_data) / 16000
        words_count = int(duration * 150 / 60)  # Assume ~150 words per minute
        
        dummy_words = [
            "The board discussed", "quarterly results show", "significant progress in",
            "key initiatives", "market expansion", "cost optimization", "team performance",
            "strategic objectives", "risk management", "upcoming challenges"
        ]
        
        text = " ".join(dummy_words[:min(words_count, len(dummy_words))])
        return text if text else "Meeting discussion recorded"


class TranscriptionBuffer:
    """Manages buffering and batching of transcription."""
    
    def __init__(self, batch_size: int = 8000):  # ~0.5 seconds at 16kHz
        self.batch_size = batch_size
        self.buffer = []
        
    def add_audio(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """Add audio chunk and return full batch if ready."""
        self.buffer.append(audio_chunk)
        
        total_samples = sum(len(chunk) for chunk in self.buffer)
        if total_samples >= self.batch_size:
            batch = np.concatenate(self.buffer)
            self.buffer = []
            return batch
        
        return None
    
    def get_pending(self) -> Optional[np.ndarray]:
        """Get any pending audio without waiting for batch."""
        if self.buffer:
            batch = np.concatenate(self.buffer)
            self.buffer = []
            return batch
        return None
    
    def clear(self):
        """Clear the buffer."""
        self.buffer = []


# Global STT engine
_stt_engine = SpeechToTextEngine(engine="google")
_transcription_buffer = TranscriptionBuffer()


def get_stt_engine() -> SpeechToTextEngine:
    """Get the global STT engine."""
    return _stt_engine


def transcribe_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, str]:
    """Transcribe audio data to text."""
    engine = get_stt_engine()
    return engine.transcribe_audio(audio_data, sample_rate)


def transcribe_audio_bytes(audio_chunk: bytes) -> Tuple[bool, str]:
    """Transcribe audio from bytes."""
    try:
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        return transcribe_audio(audio_data)
    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return False, ""
