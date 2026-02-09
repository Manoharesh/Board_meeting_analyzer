from app.ai.llm_client import call_llm

def extract_decisions(text: str):
    system = "You extract explicit board meeting decisions."

    prompt = f"""
Extract ONLY explicit decisions from the text.

Decision rules:
- Must indicate commitment or agreement
- Ignore suggestions or opinions

Text:
{text}

Return format:
{{
  "decisions": [
    {{
      "decision": "string",
      "proposed_by": "speaker or unknown",
      "confidence": "high | medium | low"
    }}
  ]
}}
"""

    return call_llm(prompt, system)
