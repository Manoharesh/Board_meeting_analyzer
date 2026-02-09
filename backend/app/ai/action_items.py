"""Action items extraction from meetings."""
import logging
from typing import List, Dict
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)

def extract_action_items(text: str) -> List[Dict]:
    """
    Extract action items from meeting text.
    
    Returns:
        List of action items with task, owner, deadline, and priority
    """
    try:
        system = "You extract action items from board meetings. Be concise and accurate."

        prompt = f"""
Extract ONLY concrete action items from the text.

Rules:
- Must assign responsibility to a person or team
- Include deadline if mentioned
- Set priority based on urgency
- Return empty list if no action items found

Text:
{text}

Return ONLY valid JSON:
{{
  "action_items": [
    {{
      "task": "clear task description",
      "owner": "person or team name",
      "deadline": "date string or null",
      "priority": "high|medium|low"
    }}
  ]
}}
"""

        result = call_llm(prompt, system)
        
        if isinstance(result, dict) and 'action_items' in result:
            items = result['action_items']
            if isinstance(items, list):
                # Validate and clean items
                cleaned_items = []
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        cleaned_item = {
                            'id': f'action_{i}',
                            'description': item.get('task', ''),
                            'owner': item.get('owner'),
                            'due_date': item.get('deadline'),
                            'priority': item.get('priority', 'medium')
                        }
                        if cleaned_item['description']:
                            cleaned_items.append(cleaned_item)
                return cleaned_items
        
        return []
        
    except Exception as e:
        logger.error(f"Error extracting action items: {e}")
        return []
