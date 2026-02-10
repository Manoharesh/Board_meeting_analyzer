import io
import logging
import subprocess
import numpy as np
from app.config import config

logger = logging.getLogger(__name__)

def decode_audio(raw_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    """
    Decodes arbitrary audio bytes (WebM, MP4, etc.) to PCM float32 at target_sr.
    Uses ffmpeg via subprocess for maximum compatibility.
    """
    if not raw_bytes:
        return np.array([], dtype=np.float32)

    try:
        # Use ffmpeg to convert input to raw PCM float32 at 16kHz mono
        command = [
            'ffmpeg',
            '-i', 'pipe:0',          # Input from stdin
            '-f', 'f32le',           # Output format: float 32-bit little endian
            '-acodec', 'pcm_f32le',  # Codec
            '-ar', str(target_sr),   # Sample rate
            '-ac', '1',               # Mono
            'pipe:1'                 # Output to stdout
        ]
        
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout_data, stderr_data = process.communicate(input=raw_bytes)
        
        if process.returncode != 0:
            logger.error("FFmpeg decoding failed: %s", stderr_data.decode())
            # Fallback to soundfile if ffmpeg fails (might work for some formats)
            try:
                import io
                import soundfile as sf
                data, sr = sf.read(io.BytesIO(raw_bytes))
                if sr != target_sr:
                    import librosa
                    data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
                return data.astype(np.float32)
            except Exception as e:
                logger.error("Fallback decoding also failed: %s", e)
                return np.array([], dtype=np.float32)

        # Convert bytes back to numpy array
        return np.frombuffer(stdout_data, dtype=np.float32)

    except Exception as exc:
        logger.error("Audio decoding exception: %s", exc)
        return np.array([], dtype=np.float32)

def is_silent(audio_data: np.ndarray, threshold: float = 0.0001) -> bool:
    """
    Checks if the audio is silent based on RMS energy.
    """
    if audio_data.size == 0:
        return True
    
    rms = np.sqrt(np.mean(np.square(audio_data)))
    logger.debug("Audio chunk RMS level: %.6f (threshold: %.6f)", rms, threshold)
    return rms < threshold

def get_audio_duration(audio_data: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Returns duration in seconds.
    """
    if audio_data.size == 0:
        return 0.0
    return len(audio_data) / sample_rate
