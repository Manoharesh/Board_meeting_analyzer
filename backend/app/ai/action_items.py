from app.ai.llm_client import call_llm

def extract_action_items(text: str):
    system = "You extract action items from board meetings."

    prompt = f"""
Extract action items from the text.

Rules:
- Must imply responsibility
- Deadline optional

Text:
{text}

Return format:
{{
  "action_items": [
    {{
      "task": "string",
      "owner": "person or team",
      "deadline": "string or null"
    }}
  ]
}}
"""

    return call_llm(prompt, system)
