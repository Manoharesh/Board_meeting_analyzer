from fastapi import APIRouter
from app.memory.meeting_store import store_chunk, get_meeting
from app.ai.summarizer import summarize 
from app.ai.decision_extractor import extract_decisions
from app.ai.action_items import extract_action_items

router = APIRouter()

@router.post("/chunk")
def add_chunk(meeting_id: str, speaker: str, text: str):
    chunk = {"speaker": speaker, "text": text}
    store_chunk(meeting_id, chunk)
    return {"status": "chunk stored"}

@router.get("/analysis")
def analyze_meeting(meeting_id: str):
    chunks = get_meeting(meeting_id)
    full_text = " ".join(c["text"] for c in chunks)

    return {
        "summary": summarize(chunks),
        "decisions": extract_decisions(full_text),
        "action_items": extract_action_items(full_text)
    }
