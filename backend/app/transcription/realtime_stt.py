import io
import logging
import wave
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SpeechToTextEngine:
    def __init__(self, engine: str = "google", timeout: float = 10.0):
        self.engine = engine
        self.timeout = timeout
        self.recognizer = None
        self.whisper_model = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialize_engines()

    def _initialize_engines(self) -> None:
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            logger.info("SpeechRecognition engine initialized")
        except Exception as exc:
            logger.warning("SpeechRecognition initialization failed: %s", exc)

        try:
            import whisper
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper engine initialized")
        except Exception as exc:
            logger.warning("Whisper initialization failed: %s", exc)

    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, str]:
        if audio_data is None or len(audio_data) == 0:
            return False, ""

        normalized = self._normalize_audio(audio_data)
        if normalized.size == 0:
            return False, ""

        engine_order = self._engine_order()
        for engine_name in engine_order:
            try:
                if engine_name == "whisper":
                    future = self.executor.submit(self._transcribe_whisper, normalized, sample_rate)
                elif engine_name == "google":
                    future = self.executor.submit(self._transcribe_google, normalized, sample_rate)
                else:
                    continue
                
                success, text = future.result(timeout=self.timeout)
                if success and text:
                    return True, text
                    
            except FutureTimeoutError:
                logger.warning("%s transcription timed out after %ss", engine_name, self.timeout)
                continue
            except Exception as exc:
                logger.error("%s transcription error: %s", engine_name, exc)
                continue

        return False, ""

    def _engine_order(self) -> Tuple[str, ...]:
        preferred = (self.engine or "").lower().strip()
        if preferred == "whisper":
            return ("whisper", "google")
        if preferred == "google":
            return ("google", "whisper")
        return ("google", "whisper")

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        data = np.asarray(audio_data, dtype=np.float32)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if data.size == 0:
            return np.array([], dtype=np.float32)
        peak = float(np.max(np.abs(data)))
        if peak > 1.0:
            data = data / 32768.0
        return np.clip(data, -1.0, 1.0).astype(np.float32)

    def _transcribe_whisper(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, str]:
        if self.whisper_model is None:
            return False, ""

        try:
            result = self.whisper_model.transcribe(audio_data, language="en", fp16=False)
            text = str(result.get("text", "")).strip() if isinstance(result, dict) else ""
            return (bool(text), text)
        except Exception as exc:
            logger.error("Whisper transcription error: %s", exc)
            return False, ""

    def _transcribe_google(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, str]:
        if self.recognizer is None:
            return False, ""

        try:
            import speech_recognition as sr

            wav_buffer = io.BytesIO()
            pcm16 = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm16.tobytes())
            wav_buffer.seek(0)

            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)

            text = self.recognizer.recognize_google(audio, language="en-US").strip()
            return (bool(text), text)
        except Exception as exc:
            logger.error("Google transcription error: %s", exc)
            return False, ""


_stt_engine = SpeechToTextEngine(engine="google", timeout=10.0)


def get_stt_engine() -> SpeechToTextEngine:
    return _stt_engine


def transcribe_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, str]:
    engine = get_stt_engine()
    return engine.transcribe_audio(audio_data, sample_rate)


def transcribe_audio_bytes(audio_chunk: bytes) -> Tuple[bool, str]:
    try:
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        return transcribe_audio(audio_data)
    except Exception as exc:
        logger.error("Error transcribing audio bytes: %s", exc)
        return False, ""
