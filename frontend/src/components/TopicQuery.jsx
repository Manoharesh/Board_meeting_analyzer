import React, { useState } from 'react';
import '../styles/TopicQuery.css';
import api from '../services/api';

const TopicQuery = ({ meetingId }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [queryType, setQueryType] = useState('semantic');

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!query.trim()) {
      setError('Please enter a question or topic');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const data = queryType === 'semantic'
        ? await api.semanticQuery(meetingId, query)
        : await api.queryByTopic(meetingId, query);

      setResults(data);
    } catch (err) {
      setError(err.message || 'Error performing search');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="topic-query">
      <div className="query-section">
        <h3>Meeting Q&A</h3>

        <div className="query-mode-toggle">
          <label>
            <input
              type="radio"
              value="semantic"
              checked={queryType === 'semantic'}
              onChange={(e) => setQueryType(e.target.value)}
            />
            Smart Q&A
          </label>
          <label>
            <input
              type="radio"
              value="topic"
              checked={queryType === 'topic'}
              onChange={(e) => setQueryType(e.target.value)}
            />
            Topic Search
          </label>
        </div>

        <form onSubmit={handleSearch} className="query-form">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={queryType === 'semantic' ? 'Ask a question about the meeting...' : 'Search for a topic...'}
            className="query-input"
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && <div className="error-message">{error}</div>}
      </div>

      {results && (
        <div className="results-section">
          {queryType === 'semantic' ? (
            <>
              <div className="answer-box">
                <h4>Answer</h4>
                <p className="answer">{results.answer}</p>
              </div>

              {results.relevant_chunks && results.relevant_chunks.length > 0 && (
                <div className="relevant-chunks">
                  <h4>Relevant Segments ({results.chunk_count})</h4>
                  <div className="chunks-list">
                    {results.relevant_chunks.map((chunk, idx) => (
                      <div key={idx} className="chunk">
                        <div className="chunk-header">
                          <span className="speaker">{chunk.speaker}</span>
                          <span className="timestamp">[{chunk.timestamp}s]</span>
                        </div>
                        <p className="chunk-text">{chunk.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="search-info">
                <p>Found {results.results_count} relevant segments</p>
              </div>

              {results.results && results.results.length > 0 ? (
                <div className="results-list">
                  {results.results.map((result, idx) => (
                    <div key={idx} className="result-item">
                      <div className="result-header">
                        <span className="speaker">{result.speaker}</span>
                        {result.sentiment && (
                          <span className={`sentiment sentiment-${result.sentiment}`}>
                            {result.sentiment}
                          </span>
                        )}
                      </div>
                      <p className="result-text">{result.text}</p>
                      {result.timestamp !== undefined && (
                        <span className="timestamp">{result.timestamp}s</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-results">
                  No results found for your search
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="quick-queries">
        <h4>Quick Queries</h4>
        <div className="query-buttons">
          {['What were the key decisions?', 'Who spoke the most?', 'What was the sentiment?'].map((q, idx) => (
            <button
              key={idx}
              className="quick-query-btn"
              onClick={() => {
                setQuery(q);
                setQueryType('semantic');
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TopicQuery;
