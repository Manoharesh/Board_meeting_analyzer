import React, { useState } from 'react';
import '../styles/DecisionBoard.css';

const DecisionBoard = ({ analysis }) => {
  const [expandedSection, setExpandedSection] = useState('summary');

  if (!analysis) {
    return <div className="decision-board">No analysis available</div>;
  }

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="decision-board">
      <section className="board-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('summary')}
        >
          <span className="icon">📝</span>
          <span className="title">Meeting Summary</span>
          <span className={`toggle ${expandedSection === 'summary' ? 'open' : ''}`}>▼</span>
        </button>
        
        {expandedSection === 'summary' && (
          <div className="section-content">
            <p className="summary-text">{analysis.summary}</p>
            
            {analysis.key_points && analysis.key_points.length > 0 && (
              <div className="key-points">
                <h4>Key Points:</h4>
                <ul>
                  {analysis.key_points.map((point, idx) => (
                    <li key={idx}>{point}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="board-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('decisions')}
        >
          <span className="icon">✅</span>
          <span className="title">Decisions ({analysis.decisions?.length || 0})</span>
          <span className={`toggle ${expandedSection === 'decisions' ? 'open' : ''}`}>▼</span>
        </button>
        
        {expandedSection === 'decisions' && (
          <div className="section-content">
            {analysis.decisions && analysis.decisions.length > 0 ? (
              <div className="items-list">
                {analysis.decisions.map((decision, idx) => (
                  <div key={idx} className="item decision-item">
                    <div className="item-header">
                      <span className="item-title">{decision.description}</span>
                      <span className={`status status-${decision.status}`}>
                        {decision.status}
                      </span>
                    </div>
                    {decision.owner && (
                      <div className="item-meta">
                        <span className="meta-label">Owner:</span>
                        <span className="meta-value">{decision.owner}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-items">No decisions found</p>
            )}
          </div>
        )}
      </section>

      <section className="board-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('actions')}
        >
          <span className="icon">🎯</span>
          <span className="title">Action Items ({analysis.action_items?.length || 0})</span>
          <span className={`toggle ${expandedSection === 'actions' ? 'open' : ''}`}>▼</span>
        </button>
        
        {expandedSection === 'actions' && (
          <div className="section-content">
            {analysis.action_items && analysis.action_items.length > 0 ? (
              <div className="items-list">
                {analysis.action_items.map((action, idx) => (
                  <div key={idx} className={`item action-item priority-${action.priority}`}>
                    <div className="item-header">
                      <span className="priority-badge">{action.priority}</span>
                      <span className="item-title">{action.description}</span>
                    </div>
                    <div className="item-details">
                      {action.owner && (
                        <div className="detail">
                          <span className="label">Owner:</span>
                          <span className="value">{action.owner}</span>
                        </div>
                      )}
                      {action.due_date && (
                        <div className="detail">
                          <span className="label">Due:</span>
                          <span className="value">{action.due_date}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-items">No action items found</p>
            )}
          </div>
        )}
      </section>

      <section className="board-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('sentiment')}
        >
          <span className="icon">😊</span>
          <span className="title">Sentiment Analysis</span>
          <span className={`toggle ${expandedSection === 'sentiment' ? 'open' : ''}`}>▼</span>
        </button>
        
        {expandedSection === 'sentiment' && (
          <div className="section-content">
            {analysis.sentiment_breakdown && Object.keys(analysis.sentiment_breakdown).length > 0 ? (
              <div className="sentiment-grid">
                {Object.entries(analysis.sentiment_breakdown).map(([speaker, data]) => (
                  <div key={speaker} className="sentiment-card">
                    <h4>{speaker}</h4>
                    <div className="sentiment-stat">
                      <span className="label">Overall Score:</span>
                      <span className={`score sentiment-${
                        data.overall_score > 0.3 ? 'positive' : data.overall_score < -0.3 ? 'negative' : 'neutral'
                      }`}>
                        {(data.overall_score).toFixed(2)}
                      </span>
                    </div>
                    <div className="sentiment-breakdown-mini">
                      <div className="breakdown-item">
                        <span>Positive: {data.positive_count}</span>
                      </div>
                      <div className="breakdown-item">
                        <span>Neutral: {data.neutral_count}</span>
                      </div>
                      <div className="breakdown-item">
                        <span>Negative: {data.negative_count}</span>
                      </div>
                    </div>
                    {data.dominant_emotion && (
                      <div className="emotion">
                        <span className="label">Dominant Emotion:</span>
                        <span className="value">{data.dominant_emotion}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-items">No sentiment data available</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
};

export default DecisionBoard;
