"""Topic-based querying of meeting content."""
import logging
from typing import List, Dict, Tuple
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)

def query_by_topic(chunks: List[Dict], topic: str) -> List[Dict]:
    """
    Query meeting chunks by topic using keyword matching and semantic search.
    
    Args:
        chunks: List of meeting chunks with speaker and text
        topic: Topic to search for
        
    Returns:
        Filtered chunks related to the topic
    """
    try:
        # First pass: simple keyword matching
        topic_lower = topic.lower()
        keyword_matches = []
        
        for chunk in chunks:
            text = chunk.get('text', '').lower()
            if topic_lower in text or any(word in text for word in topic_lower.split()):
                keyword_matches.append(chunk)
        
        return keyword_matches
        
    except Exception as e:
        logger.error(f"Error querying by topic: {e}")
        return []


def semantic_query(chunks: List[Dict], query: str) -> Tuple[List[Dict], str]:
    """
    Perform semantic search on meeting content using LLM.
    
    Args:
        chunks: List of meeting chunks
        query: Natural language query
        
    Returns:
        (relevant_chunks, answer_summary)
    """
    try:
        # Prepare context from chunks
        chunks_text = "\n".join([f"{c.get('speaker', 'Unknown')}: {c.get('text', '')}" for c in chunks[:20]])  # Limit for context
        
        system = "You answer questions about board meetings using the provided transcript."
        
        prompt = f"""
Based on the meeting transcript below, answer the following question:

Question: {query}

Transcript:
{chunks_text}

Provide a concise, factual answer.
"""
        
        result = call_llm(prompt, system)
        
        if isinstance(result, dict):
            answer = result.get('answer', str(result))
        else:
            answer = str(result)
        
        # Return relevant chunks and answer
        relevant = query_by_topic(chunks, query.split()[0] if query.split() else query)
        
        return relevant, answer
        
    except Exception as e:
        logger.error(f"Error in semantic query: {e}")
        return [], f"Error processing query: {str(e)}"
