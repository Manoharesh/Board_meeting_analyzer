import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/MeetingView.css';
import LiveTranscript from '../components/LiveTranscript';
import DecisionBoard from '../components/DecisionBoard';
import SentimentTimeline from '../components/SentimentTimeline';
import TopicQuery from '../components/TopicQuery';

const MeetingView = ({ meeting, onEndMeeting, isRecording }) => {
  const [activeTab, setActiveTab] = useState('transcript');
  const [transcript, setTranscript] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [speakers, setSpeakers] = useState([]);
  const [loading, setLoading] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);

  useEffect(() => {
    if (isRecording) {
      startAudioCapture();
    }
    
    return () => {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording, startAudioCapture]);

  // Load meeting data periodically
  useEffect(() => {
    const interval = setInterval(() => {
      loadMeetingData();
    }, 5000); // Update every 5 seconds
    
    return () => clearInterval(interval);
  }, [meeting.id, loadMeetingData]);

  const startAudioCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      let audioChunks = [];
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await sendAudioChunk(audioBlob);
        audioChunks = [];
        
        // Restart recording
        if (isRecording) {
          mediaRecorder.start();
        }
      };
      
      mediaRecorder.start();
      
      // Send chunks every 3 seconds
      const chunkInterval = setInterval(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
      }, 3000);
      
      return () => clearInterval(chunkInterval);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  }, [isRecording]);

  const sendAudioChunk = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('chunk', audioBlob);
      
      const response = await fetch(`/api/meeting/audio-chunk/${meeting.id}`, {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        await loadMeetingData();
      }
    } catch (error) {
      console.error('Error sending audio chunk:', error);
    }
  };

  const loadMeetingData = useCallback(async () => {
    try {
      // Load transcript
      const transcriptRes = await fetch(`/api/meeting/transcript/${meeting.id}`);
      if (transcriptRes.ok) {
        const transcriptData = await transcriptRes.json();
        setTranscript(transcriptData.transcript || []);
      }
      
      // Load speakers
      const speakersRes = await fetch(`/api/query/speakers/${meeting.id}`);
      if (speakersRes.ok) {
        const speakersData = await speakersRes.json();
        setSpeakers(speakersData.speakers || []);
      }
    } catch (error) {
      console.error('Error loading meeting data:', error);
    }
  }, [meeting.id]);

  const handleGenerateAnalysis = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/meeting/analysis/${meeting.id}`);
      if (response.ok) {
        const data = await response.json();
        setAnalysis(data);
        setActiveTab('analysis');
      }
    } catch (error) {
      console.error('Error generating analysis:', error);
      alert('Error generating analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="meeting-view">
      <div className="meeting-header">
        <div className="meeting-title-section">
          <h2>🎙️ {meeting.name}</h2>
          <p className="meeting-id">ID: {meeting.id}</p>
        </div>
        
        <div className="meeting-controls">
          {isRecording && (
            <button 
              className="btn btn-primary"
              onClick={handleGenerateAnalysis}
              disabled={loading}
            >
              {loading ? '⏳ Analyzing...' : '📊 Generate Analysis'}
            </button>
          )}
          <button 
            className="btn btn-danger"
            onClick={onEndMeeting}
          >
            ⏹️ End Meeting
          </button>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'transcript' ? 'active' : ''}`}
          onClick={() => setActiveTab('transcript')}
        >
          📝 Transcript ({transcript.length})
        </button>
        <button
          className={`tab ${activeTab === 'speakers' ? 'active' : ''}`}
          onClick={() => setActiveTab('speakers')}
        >
          👥 Speakers ({speakers.length})
        </button>
        <button
          className={`tab ${activeTab === 'sentiment' ? 'active' : ''}`}
          onClick={() => setActiveTab('sentiment')}
        >
          😊 Sentiment
        </button>
        <button
          className={`tab ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          📊 Analysis
        </button>
        <button
          className={`tab ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab('query')}
        >
          ❓ Q&A
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'transcript' && (
          <LiveTranscript transcript={transcript} />
        )}
        
        {activeTab === 'speakers' && (
          <div className="speakers-section">
            <h3>Meeting Speakers</h3>
            {speakers.length > 0 ? (
              <div className="speakers-grid">
                {speakers.map((speaker, idx) => (
                  <div key={idx} className="speaker-card">
                    <h4>{speaker.name}</h4>
                    <div className="speaker-stats">
                      <div className="stat">
                        <span className="label">Contributions:</span>
                        <span className="value">{speaker.contributions}</span>
                      </div>
                      <div className="sentiment-breakdown">
                        {speaker.sentiment_breakdown && (
                          <>
                            <span className="label">Sentiment:</span>
                            <div className="sentiment-bars">
                              {Object.entries(speaker.sentiment_breakdown).map(([sentiment, count]) => (
                                <div key={sentiment} className={`bar sentiment-${sentiment}`}>
                                  <span>{sentiment}: {count}</span>
                                </div>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No speakers detected yet</p>
            )}
          </div>
        )}
        
        {activeTab === 'sentiment' && (
          <SentimentTimeline transcript={transcript} />
        )}
        
        {activeTab === 'analysis' && (
          analysis ? (
            <DecisionBoard analysis={analysis} />
          ) : (
            <div className="no-analysis">
              <p>Click "Generate Analysis" to analyze the meeting</p>
            </div>
          )
        )}
        
        {activeTab === 'query' && (
          <TopicQuery meetingId={meeting.id} />
        )}
      </div>
    </div>
  );
};

export default MeetingView;
