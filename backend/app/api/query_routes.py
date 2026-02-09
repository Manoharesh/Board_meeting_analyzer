from fastapi import APIRouter
from app.memory.meeting_store import get_meeting
from app.ai.topic_query import query_by_topic

router = APIRouter()

@router.get("/topic")
def topic_query(meeting_id: str, topic: str):
    chunks = get_meeting(meeting_id)
    return query_by_topic(chunks, topic)
