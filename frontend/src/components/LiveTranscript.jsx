import React from 'react';
import '../styles/LiveTranscript.css';

const LiveTranscript = ({ transcript }) => {
  const endRef = React.useRef(null);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  if (!transcript || transcript.length === 0) {
    return (
      <div className="live-transcript">
        <div className="empty-state">
          <p>Waiting for audio input...</p>
          <p className="hint">Make sure your microphone is active</p>
        </div>
      </div>
    );
  }

  return (
    <div className="live-transcript">
      <div className="transcript-header">
        <h3>Live Transcript</h3>
        <span className="entry-count">{transcript.length} entries</span>
      </div>
      
      <div className="transcript-entries">
        {transcript.map((entry, idx) => (
          <div 
            key={idx}
            className={`entry sentiment-${entry.sentiment || 'neutral'}`}
          >
            <div className="entry-header">
              <span className="speaker">{entry.speaker}</span>
              <span className="timestamp">
                {entry.timestamp ? `[${entry.timestamp}s]` : ''}
              </span>
              {entry.sentiment && (
                <span className={`sentiment-badge sentiment-${entry.sentiment}`}>
                  {entry.sentiment}
                </span>
              )}
            </div>
            <div className="entry-text">
              {entry.text}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
};

export default LiveTranscript;
