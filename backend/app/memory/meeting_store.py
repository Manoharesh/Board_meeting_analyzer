"""
Meeting storage module.
Stores meeting data including metadata, transcript, and analysis.
Can be extended to use a database (MongoDB, PostgreSQL, etc.).
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.models.schemas import MeetingMetadata, TranscriptEntry, MeetingAnalysis, AudioChunk

logger = logging.getLogger(__name__)

class MeetingStore:
    """Stores and retrieves meeting data."""
    
    def __init__(self):
        self.meetings: Dict[str, Dict] = {}  # {meeting_id: meeting_data}
        self.meeting_metadata: Dict[str, MeetingMetadata] = {}
        self.meeting_transcripts: Dict[str, List[TranscriptEntry]] = {}
        self.meeting_analysis: Dict[str, MeetingAnalysis] = {}
        
    def create_meeting(self, meeting_id: str, meeting_name: str, 
                      participants: List[str] = None) -> MeetingMetadata:
        """Create a new meeting."""
        try:
            if meeting_id in self.meetings:
                logger.warning(f"Meeting {meeting_id} already exists")
                return self.meeting_metadata[meeting_id]
            
            metadata = MeetingMetadata(
                meeting_id=meeting_id,
                meeting_name=meeting_name,
                start_time=datetime.now(),
                participants=participants or []
            )
            
            self.meetings[meeting_id] = {
                'metadata': metadata,
                'chunks': [],
                'transcript': [],
                'analysis': None,
                'created_at': datetime.now()
            }
            
            self.meeting_metadata[meeting_id] = metadata
            self.meeting_transcripts[meeting_id] = []
            
            logger.info(f"Created meeting: {meeting_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            raise
    
    def end_meeting(self, meeting_id: str) -> bool:
        """Mark meeting as ended."""
        try:
            if meeting_id not in self.meetings:
                return False
            
            metadata = self.meeting_metadata[meeting_id]
            metadata.end_time = datetime.now()
            
            # Calculate duration and check for audio chunks
            duration = (metadata.end_time - metadata.start_time).total_seconds()
            chunk_count = len(self.meetings[meeting_id].get('chunks', []))
            
            if duration < 10 or chunk_count == 0:
                metadata.status = "no_audio"
                logger.info(f"Meeting {meeting_id} marked as no_audio (duration: {duration:.1f}s, chunks: {chunk_count})")
            else:
                metadata.status = "completed"
            
            logger.info(f"Ended meeting: {meeting_id} with status: {metadata.status}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending meeting: {e}")
            return False
    
    def store_chunk(self, meeting_id: str, chunk: Dict) -> bool:
        """Store an audio chunk with transcription."""
        try:
            if meeting_id not in self.meetings:
                logger.warning(f"Meeting {meeting_id} not found")
                return False
            
            self.meetings[meeting_id]['chunks'].append(chunk)
            return True
            
        except Exception as e:
            logger.error(f"Error storing chunk: {e}")
            return False
    
    def store_transcript_entry(self, meeting_id: str, entry: TranscriptEntry) -> bool:
        """Store a transcript entry."""
        try:
            if meeting_id not in self.meetings:
                return False
            
            self.meeting_transcripts[meeting_id].append(entry)
            self.meetings[meeting_id]['transcript'].append(entry)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing transcript entry: {e}")
            return False
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict]:
        """Get complete meeting data."""
        return self.meetings.get(meeting_id)
    
    def get_meeting_metadata(self, meeting_id: str) -> Optional[MeetingMetadata]:
        """Get meeting metadata."""
        return self.meeting_metadata.get(meeting_id)
    
    def get_meeting_chunks(self, meeting_id: str) -> List[Dict]:
        """Get all chunks for a meeting."""
        meeting = self.meetings.get(meeting_id)
        if meeting:
            return meeting['chunks']
        return []
    
    def get_meeting_transcript(self, meeting_id: str) -> List[TranscriptEntry]:
        """Get transcript for a meeting."""
        return self.meeting_transcripts.get(meeting_id, [])
    
    def get_meeting_full_text(self, meeting_id: str) -> str:
        """Get full meeting text as a single string."""
        chunks = self.get_meeting_chunks(meeting_id)
        if not chunks:
            return ""
        
        text_parts = []
        for chunk in chunks:
            speaker = chunk.get('speaker', 'Unknown')
            text = chunk.get('text', '')
            text_parts.append(f"{speaker}: {text}")
        
        return "\n".join(text_parts)
    
    def store_analysis(self, meeting_id: str, analysis: MeetingAnalysis) -> bool:
        """Store meeting analysis."""
        try:
            if meeting_id not in self.meetings:
                return False
            
            self.meeting_analysis[meeting_id] = analysis
            self.meetings[meeting_id]['analysis'] = analysis
            
            logger.info(f"Stored analysis for meeting: {meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing analysis: {e}")
            return False
    
    def get_analysis(self, meeting_id: str) -> Optional[MeetingAnalysis]:
        """Get meeting analysis."""
        return self.meeting_analysis.get(meeting_id)
    
    def list_meetings(self) -> List[Dict]:
        """List all meetings with basic info."""
        meetings_list = []
        for meeting_id, data in self.meetings.items():
            metadata = data.get('metadata')
            if metadata:
                meetings_list.append({
                    'meeting_id': meeting_id,
                    'name': metadata.meeting_name,
                    'start_time': metadata.start_time.isoformat() if metadata.start_time else None,
                    'end_time': metadata.end_time.isoformat() if metadata.end_time else None,
                    'participants': metadata.participants,
                    'chunk_count': len(data.get('chunks', []))
                })
        
        return meetings_list
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting."""
        try:
            if meeting_id in self.meetings:
                del self.meetings[meeting_id]
            if meeting_id in self.meeting_metadata:
                del self.meeting_metadata[meeting_id]
            if meeting_id in self.meeting_transcripts:
                del self.meeting_transcripts[meeting_id]
            if meeting_id in self.meeting_analysis:
                del self.meeting_analysis[meeting_id]
            
            logger.info(f"Deleted meeting: {meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting meeting: {e}")
            return False
    
    def reset(self):
        """Reset all meetings (for testing)."""
        self.meetings.clear()
        self.meeting_metadata.clear()
        self.meeting_transcripts.clear()
        self.meeting_analysis.clear()
        logger.info("Meeting store reset")


# Global meeting store
_meeting_store = MeetingStore()


def get_store() -> MeetingStore:
    """Get the global meeting store."""
    return _meeting_store


def create_meeting(meeting_id: str, meeting_name: str, 
                  participants: List[str] = None) -> MeetingMetadata:
    """Create a new meeting."""
    store = get_store()
    return store.create_meeting(meeting_id, meeting_name, participants)


def end_meeting(meeting_id: str) -> bool:
    """End a meeting."""
    store = get_store()
    return store.end_meeting(meeting_id)


def store_chunk(meeting_id: str, chunk: Dict) -> bool:
    """Store an audio chunk."""
    store = get_store()
    return store.store_chunk(meeting_id, chunk)


def get_meeting(meeting_id: str) -> Optional[Dict]:
    """Get meeting data."""
    store = get_store()
    return store.get_meeting(meeting_id)


def get_chunks(meeting_id: str) -> List[Dict]:
    """Get meeting chunks."""
    store = get_store()
    return store.get_meeting_chunks(meeting_id)


def get_full_text(meeting_id: str) -> str:
    """Get full meeting text."""
    store = get_store()
    return store.get_meeting_full_text(meeting_id)
