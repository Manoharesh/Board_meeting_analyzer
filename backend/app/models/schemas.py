from pydantic import BaseModel
from typing import List

class Chunk(BaseModel):
    meeting_id: str
    speaker: str
    text: str

class MeetingSummary(BaseModel):
    meeting_id: str
    summary: str
    decisions: List[str]
