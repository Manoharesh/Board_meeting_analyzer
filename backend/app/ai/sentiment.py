from app.ai.llm_client import call_llm

def analyze_sentiment(text: str):
    system = "You analyze sentiment in board meetings."

    prompt = f"""
Analyze the sentiment of the following statement.

Text:
{text}

Return format:
{{
  "sentiment": "positive | neutral | negative",
  "emotion": "confidence | concern | disagreement | optimism | neutral",
  "confidence": 0.0
}}
"""

    return call_llm(prompt, system)
