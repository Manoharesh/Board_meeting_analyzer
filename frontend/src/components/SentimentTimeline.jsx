import React, { useState, useEffect } from 'react';
import '../styles/SentimentTimeline.css';

const SentimentTimeline = ({ transcript }) => {
  const [sentimentData, setSentimentData] = useState([]);

  useEffect(() => {
    // Process transcript to create sentiment timeline
    if (transcript && transcript.length > 0) {
      const processed = transcript.map((entry, idx) => ({
        idx,
        speaker: entry.speaker,
        sentiment: entry.sentiment || 'neutral',
        text: `${(entry.text || '').slice(0, 50)}...`
      }));
      setSentimentData(processed);
    } else {
      setSentimentData([]);
    }
  }, [transcript]);

  const sentimentColors = {
    positive: '#10b981',
    neutral: '#6b7280',
    negative: '#ef4444'
  };

  const getSentimentPercentage = () => {
    if (sentimentData.length === 0) return { positive: 0, neutral: 0, negative: 0 };
    
    const counts = {
      positive: 0,
      neutral: 0,
      negative: 0
    };

    sentimentData.forEach(item => {
      counts[item.sentiment] = (counts[item.sentiment] || 0) + 1;
    });

    return {
      positive: (counts.positive / sentimentData.length) * 100,
      neutral: (counts.neutral / sentimentData.length) * 100,
      negative: (counts.negative / sentimentData.length) * 100
    };
  };

  const sentimentPct = getSentimentPercentage();
  const uniqueSpeakerCount = new Set(
    sentimentData.map((item) => item.speaker).filter(Boolean)
  ).size;

  if (sentimentData.length === 0) {
    return (
      <div className="sentiment-timeline">
        <div className="empty-state">
          <p>No sentiment data yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="sentiment-timeline">
      <div className="sentiment-summary">
        <h3>Sentiment Overview</h3>
        <div className="sentiment-bars">
          <div className="bar-container">
            <div className="bar-label">Positive</div>
            <div className="bar-background">
              <div 
                className="bar-fill positive"
                style={{ width: `${sentimentPct.positive}%` }}
              >
                {sentimentPct.positive > 10 && <span>{sentimentPct.positive.toFixed(1)}%</span>}
              </div>
            </div>
          </div>
          
          <div className="bar-container">
            <div className="bar-label">Neutral</div>
            <div className="bar-background">
              <div 
                className="bar-fill neutral"
                style={{ width: `${sentimentPct.neutral}%` }}
              >
                {sentimentPct.neutral > 10 && <span>{sentimentPct.neutral.toFixed(1)}%</span>}
              </div>
            </div>
          </div>
          
          <div className="bar-container">
            <div className="bar-label">Negative</div>
            <div className="bar-background">
              <div 
                className="bar-fill negative"
                style={{ width: `${sentimentPct.negative}%` }}
              >
                {sentimentPct.negative > 10 && <span>{sentimentPct.negative.toFixed(1)}%</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="timeline">
        <h3>Timeline</h3>
        <div className="timeline-items">
          {sentimentData.map((item, idx) => (
            <div 
              key={idx}
              className={`timeline-item sentiment-${item.sentiment}`}
              title={item.text}
            >
              <div className="timeline-marker" style={{ backgroundColor: sentimentColors[item.sentiment] }} />
              <div className="timeline-content">
                <div className="speaker">{item.speaker}</div>
                <div className="text">{item.text}</div>
                <div className="sentiment-label">{item.sentiment}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="sentiment-stats">
        <h3>Statistics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{sentimentData.length}</span>
            <span className="stat-label">Total Statements</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{uniqueSpeakerCount}</span>
            <span className="stat-label">Unique Speakers</span>
          </div>
          <div className="stat-card">
            <span className="stat-value positive">{
              sentimentData.filter(item => item.sentiment === 'positive').length
            }</span>
            <span className="stat-label">Positive</span>
          </div>
          <div className="stat-card">
            <span className="stat-value negative">{
              sentimentData.filter(item => item.sentiment === 'negative').length
            }</span>
            <span className="stat-label">Negative</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SentimentTimeline;
