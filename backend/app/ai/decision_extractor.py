"""Decision extraction from meetings."""
import logging
from typing import List, Dict
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)

def extract_decisions(text: str) -> List[Dict]:
    """
    Extract explicit decisions from meeting text.
    
    Returns:
        List of decisions with description, proposer, and confidence
    """
    try:
        system = "You extract ONLY explicit board meeting decisions. Ignore suggestions or opinions."

        prompt = f"""
Extract ONLY explicit decisions from the text.

Decision rules:
- Must indicate commitment, agreement, or formal decision
- Ignore suggestions, questions, or opinions
- Include who proposed/made the decision if mentioned
- Return empty if no clear decisions found

Text:
{text}

Return ONLY valid JSON:
{{
  "decisions": [
    {{
      "decision": "clear decision statement",
      "proposed_by": "person name or unknown",
      "status": "decided|pending|rejected"
    }}
  ]
}}
"""

        result = call_llm(prompt, system)
        
        if isinstance(result, dict) and 'decisions' in result:
            decisions = result['decisions']
            if isinstance(decisions, list):
                # Validate and clean decisions
                cleaned_decisions = []
                for i, decision in enumerate(decisions):
                    if isinstance(decision, dict):
                        cleaned_decision = {
                            'id': f'decision_{i}',
                            'description': decision.get('decision', ''),
                            'owner': decision.get('proposed_by'),
                            'status': decision.get('status', 'decided')
                        }
                        if cleaned_decision['description']:
                            cleaned_decisions.append(cleaned_decision)
                return cleaned_decisions
        
        return []
        
    except Exception as e:
        logger.error(f"Error extracting decisions: {e}")
        return []
