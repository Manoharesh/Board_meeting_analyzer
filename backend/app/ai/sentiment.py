"""
Sentiment analysis module.
Analyzes sentiment and emotion of speakers' statements.
Tracks sentiment breakdown by speaker over time.
"""
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from app.ai.llm_client import call_llm

logger = logging.getLogger(__name__)

# Sentiment mappings
SENTIMENT_SCORES = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0
}

EMOTION_TYPES = [
    "confidence", "concern", "disagreement", "optimism", "enthusiasm",
    "skepticism", "frustration", "agreement", "neutral", "thoughtful"
]


class SentimentAnalyzer:
    """Analyzes and tracks sentiment in meetings."""
    
    def __init__(self):
        self.speaker_sentiments: Dict[str, List[Dict]] = defaultdict(list)
        self.overall_sentiment: Dict[str, float] = {}
        
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of the given text.
        
        Returns:
            {
                "sentiment": "positive|neutral|negative",
                "emotion": "emotion_type",
                "confidence": 0.0-1.0,
                "score": -1.0 to 1.0
            }
        """
        try:
            system = "You analyze sentiment and emotion in board meetings. Be concise."

            prompt = f"""
Analyze the sentiment and emotion of the following statement.

Text:
{text}

Return ONLY valid JSON:
{{
  "sentiment": "positive|neutral|negative",
  "emotion": "confidence|concern|disagreement|optimism|enthusiasm|skepticism|frustration|agreement|neutral|thoughtful",
  "confidence": 0.0
}}
"""
            
            result = call_llm(prompt, system)
            
            # Ensure we have valid sentiment
            if isinstance(result, dict):
                sentiment = result.get('sentiment', 'neutral').lower()
                if sentiment not in SENTIMENT_SCORES:
                    sentiment = 'neutral'
                    
                score = SENTIMENT_SCORES.get(sentiment, 0.0)
                confidence = float(result.get('confidence', 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                
                return {
                    "sentiment": sentiment,
                    "emotion": result.get('emotion', 'neutral'),
                    "confidence": confidence,
                    "score": score
                }
            
            return {
                "sentiment": "neutral",
                "emotion": "neutral",
                "confidence": 0.0,
                "score": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "emotion": "neutral",
                "confidence": 0.0,
                "score": 0.0
            }
    
    def track_speaker_sentiment(self, speaker_name: str, text: str) -> Dict:
        """
        Analyze and track sentiment for a specific speaker.
        
        Returns: Sentiment analysis result
        """
        sentiment_result = self.analyze_sentiment(text)
        
        # Store in history
        self.speaker_sentiments[speaker_name].append({
            "text": text[:100],  # Store first 100 chars
            "sentiment": sentiment_result,
            "timestamp": len(self.speaker_sentiments[speaker_name])  # Sequential ID
        })
        
        # Update overall sentiment for speaker
        self._update_speaker_overall(speaker_name)
        
        return sentiment_result
    
    def _update_speaker_overall(self, speaker_name: str):
        """Update overall sentiment score for speaker."""
        sentiments = self.speaker_sentiments.get(speaker_name, [])
        if sentiments:
            scores = [s['sentiment'].get('score', 0.0) for s in sentiments]
            self.overall_sentiment[speaker_name] = sum(scores) / len(scores)
        else:
            self.overall_sentiment[speaker_name] = 0.0
    
    def get_speaker_sentiment_breakdown(self) -> Dict[str, Dict]:
        """
        Get sentiment breakdown for all speakers.
        
        Returns:
            {
                "speaker_name": {
                    "overall_score": -1.0 to 1.0,
                    "statement_count": int,
                    "positive_count": int,
                    "negative_count": int,
                    "neutral_count": int,
                    "dominant_emotion": str
                }
            }
        """
        breakdown = {}
        
        for speaker_name, sentiments in self.speaker_sentiments.items():
            if not sentiments:
                continue
                
            positive_count = sum(1 for s in sentiments if s['sentiment']['sentiment'] == 'positive')
            negative_count = sum(1 for s in sentiments if s['sentiment']['sentiment'] == 'negative')
            neutral_count = sum(1 for s in sentiments if s['sentiment']['sentiment'] == 'neutral')
            
            # Get dominant emotion
            emotions = {}
            for s in sentiments:
                emotion = s['sentiment'].get('emotion', 'neutral')
                emotions[emotion] = emotions.get(emotion, 0) + 1
            
            dominant_emotion = max(emotions, key=emotions.get) if emotions else 'neutral'
            
            breakdown[speaker_name] = {
                "overall_score": self.overall_sentiment.get(speaker_name, 0.0),
                "statement_count": len(sentiments),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "dominant_emotion": dominant_emotion,
                "emotions": emotions
            }
        
        return breakdown
    
    def get_speaker_sentiments(self, speaker_name: str) -> List[Dict]:
        """Get sentiment history for a specific speaker."""
        return self.speaker_sentiments.get(speaker_name, [])
    
    def reset(self):
        """Reset sentiment tracking for new meeting."""
        self.speaker_sentiments.clear()
        self.overall_sentiment.clear()
        logger.info("Sentiment tracking reset")


# Global sentiment analyzer
_sentiment_analyzer = SentimentAnalyzer()


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get the global sentiment analyzer."""
    return _sentiment_analyzer


def analyze_sentiment(text: str) -> Dict:
    """Analyze sentiment of text."""
    analyzer = get_sentiment_analyzer()
    return analyzer.analyze_sentiment(text)


def track_speaker_sentiment(speaker_name: str, text: str) -> Dict:
    """Track sentiment for a speaker."""
    analyzer = get_sentiment_analyzer()
    return analyzer.track_speaker_sentiment(speaker_name, text)


def get_sentiment_breakdown() -> Dict[str, Dict]:
    """Get sentiment breakdown for all speakers."""
    analyzer = get_sentiment_analyzer()
    return analyzer.get_speaker_sentiment_breakdown()
