from app.ai.llm_client import call_llm

def summarize(chunks, length="short", focus_topic=None):
    text = "\n".join(
        [f"{c['speaker']}: {c['text']}" for c in chunks]
    )

    system = "You summarize board meetings accurately."

    topic_clause = f"Focus ONLY on topic: {focus_topic}" if focus_topic else ""

    prompt = f"""
Summarize the meeting.

Summary length: {length}
{topic_clause}

Conversation:
{text}

Return format:
{{
  "summary": "string",
  "key_points": ["point1", "point2"]
}}
"""

    return call_llm(prompt, system)
