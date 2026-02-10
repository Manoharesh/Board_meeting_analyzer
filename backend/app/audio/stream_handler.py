import logging
from threading import Lock
from time import time
from typing import Dict, List

logger = logging.getLogger(__name__)


class AudioStreamHandler:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._sessions: Dict[str, Dict] = {}
        self._lock = Lock()

    def start_recording(self, meeting_id: str) -> None:
        with self._lock:
            self._sessions[meeting_id] = {
                "is_recording": True,
                "raw_chunks": [],
                "started_at": time(),
                "stopped_at": None,
            }
        logger.info("Audio recording started for meeting %s", meeting_id)

    def stop_recording(self, meeting_id: str) -> Dict:
        with self._lock:
            session = self._sessions.get(meeting_id)
            if not session:
                return {
                    "meeting_id": meeting_id,
                    "raw_chunks": [],
                    "chunk_count": 0,
                    "started_at": None,
                    "stopped_at": time(),
                }

            session["is_recording"] = False
            session["stopped_at"] = time()
            raw_chunks = list(session.get("raw_chunks", []))
            started_at = session.get("started_at")
            stopped_at = session.get("stopped_at")

        logger.info("Audio recording stopped for meeting %s with %s chunks", meeting_id, len(raw_chunks))
        return {
            "meeting_id": meeting_id,
            "raw_chunks": raw_chunks,
            "chunk_count": len(raw_chunks),
            "started_at": started_at,
            "stopped_at": stopped_at,
        }

    def process_audio_chunk(self, meeting_id: str, chunk: bytes) -> None:
        if not chunk:
            return

        with self._lock:
            session = self._sessions.get(meeting_id)
            if not session:
                session = {
                    "is_recording": True,
                    "raw_chunks": [],
                    "started_at": time(),
                    "stopped_at": None,
                }
                self._sessions[meeting_id] = session

            if not session.get("is_recording", False):
                return

            session["raw_chunks"].append(bytes(chunk))

    def get_recorded_chunks(self, meeting_id: str) -> List[bytes]:
        with self._lock:
            session = self._sessions.get(meeting_id)
            if not session:
                return []
            return list(session.get("raw_chunks", []))

    def clear_recording(self, meeting_id: str) -> None:
        with self._lock:
            self._sessions.pop(meeting_id, None)


_stream_handler = AudioStreamHandler()


def get_stream_handler() -> AudioStreamHandler:
    return _stream_handler


def receive_audio_chunk(meeting_id: str, chunk: bytes) -> dict:
    handler = get_stream_handler()
    handler.process_audio_chunk(meeting_id, chunk)
    return {"status": "chunk received", "meeting_id": meeting_id, "size": len(chunk)}
