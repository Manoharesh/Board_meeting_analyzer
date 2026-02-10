from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

# Meeting-related schemas
class MeetingMetadata(BaseModel):
    meeting_id: str
    meeting_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    participants: List[str] = []
    created_at: datetime = None
    status: str = "active"  # active, completed, failed

    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)

# Audio chunk with speaker info and sentiment
class AudioChunk(BaseModel):
    meeting_id: str
    speaker_id: str
    speaker_name: Optional[str] = None
    text: str
    timestamp: float
    duration: float
    sentiment: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[float] = None

# Transcript entry
class TranscriptEntry(BaseModel):
    speaker_name: str
    speaker_id: str
    text: str
    timestamp: float
    duration: float
    sentiment: Optional[str] = None

class Chunk(BaseModel):
    meeting_id: str
    speaker: str
    text: str

# Summary and decisions
class MeetingSummary(BaseModel):
    meeting_id: str
    summary: str
    key_points: List[str]

class DecisionItem(BaseModel):
    id: str
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "open"

class ActionItem(BaseModel):
    id: str
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"

# Meeting analysis result
class MeetingAnalysis(BaseModel):
    meeting_id: str
    summary: str
    key_points: List[str]
    decisions: List[DecisionItem]
    action_items: List[ActionItem]
    sentiment_breakdown: Dict[str, Dict]  # {speaker_name: {sentiment: score}}
    speakers: List[str]

# Speaker voice enrollment
class SpeakerEnrollment(BaseModel):
    speaker_id: str
    speaker_name: str
    enrollment_audio: bytes
    enrolled_at: datetime = None

    def __init__(self, **data):
        if data.get('enrolled_at') is None:
            data['enrolled_at'] = datetime.now()
        super().__init__(**data)

# Query response
class QueryResponse(BaseModel):
    query: str
    answer: str
    relevant_chunks: List[TranscriptEntry]
    confidence: float

# Meeting result with all details
class MeetingData(BaseModel):
    metadata: MeetingMetadata
    transcript: List[TranscriptEntry]
    analysis: MeetingAnalysis
    recorded_at: datetime = None

    def __init__(self, **data):
        if data.get('recorded_at') is None:
            data['recorded_at'] = datetime.now()
        super().__init__(**data)
