import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/MeetingView.css';
import LiveTranscript from '../components/LiveTranscript';
import DecisionBoard from '../components/DecisionBoard';
import SentimentTimeline from '../components/SentimentTimeline';
import TopicQuery from '../components/TopicQuery';
import api from '../services/api';

const MeetingView = ({ meeting, onEndMeeting, isRecording }) => {
  const [activeTab, setActiveTab] = useState('transcript');
  const [transcript, setTranscript] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [speakers, setSpeakers] = useState([]);
  const [loading, setLoading] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const inFlightControllersRef = useRef(new Set());
  const isEndingRef = useRef(false);
  const isMountedRef = useRef(true);
  const chunkUploadInFlightRef = useRef(false);
  const meetingDataRequestInFlightRef = useRef(false);

  const createRequestController = useCallback(() => {
    const controller = new AbortController();
    inFlightControllersRef.current.add(controller);
    return controller;
  }, []);

  const releaseRequestController = useCallback((controller) => {
    inFlightControllersRef.current.delete(controller);
  }, []);

  const abortInFlightRequests = useCallback(() => {
    inFlightControllersRef.current.forEach((controller) => controller.abort());
    inFlightControllersRef.current.clear();
  }, []);

  const loadMeetingData = useCallback(async () => {
    if (isEndingRef.current || meetingDataRequestInFlightRef.current) {
      return;
    }

    meetingDataRequestInFlightRef.current = true;
    const controller = createRequestController();
    try {
      const [transcriptData, speakersData] = await Promise.all([
        api.getTranscript(meeting.id, { signal: controller.signal }),
        api.getSpeakers(meeting.id, { signal: controller.signal })
      ]);

      if (!controller.signal.aborted && isMountedRef.current && !isEndingRef.current) {
        setTranscript(Array.isArray(transcriptData.transcript) ? transcriptData.transcript : []);
        setSpeakers(Array.isArray(speakersData.speakers) ? speakersData.speakers : []);
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error loading meeting data:', error);
      }
    } finally {
      meetingDataRequestInFlightRef.current = false;
      releaseRequestController(controller);
    }
  }, [createRequestController, meeting.id, releaseRequestController]);

  const sendAudioChunk = useCallback(async (audioBlob) => {
    if (!audioBlob || audioBlob.size === 0 || isEndingRef.current || chunkUploadInFlightRef.current) {
      return;
    }

    const controller = createRequestController();
    chunkUploadInFlightRef.current = true;
    try {
      await api.sendAudioChunk(meeting.id, audioBlob, { signal: controller.signal });
      if (!controller.signal.aborted && !isEndingRef.current) {
        await loadMeetingData();
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error sending audio chunk:', error);
      }
    } finally {
      chunkUploadInFlightRef.current = false;
      releaseRequestController(controller);
    }
  }, [createRequestController, meeting.id, loadMeetingData, releaseRequestController]);

  const stopAudioCapture = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      recorder.ondataavailable = null;
      recorder.onerror = null;
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    }
    mediaRecorderRef.current = null;

    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  }, []);

  const clearPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const cleanupMeetingActivity = useCallback(() => {
    isEndingRef.current = true;
    chunkUploadInFlightRef.current = false;
    meetingDataRequestInFlightRef.current = false;
    clearPolling();
    stopAudioCapture();
    abortInFlightRequests();
  }, [abortInFlightRequests, clearPolling, stopAudioCapture]);

  const startAudioCapture = useCallback(async () => {
    if (!meeting?.id || mediaRecorderRef.current?.state === 'recording' || isEndingRef.current) {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0 && !isEndingRef.current) {
          await sendAudioChunk(event.data);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
      };

      // Emit chunks every 3 seconds.
      mediaRecorder.start(3000);
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  }, [meeting?.id, sendAudioChunk]);

  // Load meeting data periodically.
  useEffect(() => {
    isEndingRef.current = false;
    loadMeetingData();
    clearPolling();
    pollingIntervalRef.current = setInterval(() => {
      loadMeetingData();
    }, 5000);
    return () => clearPolling();
  }, [clearPolling, loadMeetingData]);

  // Start or stop capture based on recording state.
  useEffect(() => {
    if (isRecording) {
      startAudioCapture();
    } else {
      stopAudioCapture();
    }

    return () => stopAudioCapture();
  }, [isRecording, startAudioCapture, stopAudioCapture]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      cleanupMeetingActivity();
    };
  }, [cleanupMeetingActivity]);

  const handleGenerateAnalysis = async () => {
    if (isEndingRef.current) {
      return;
    }

    const controller = createRequestController();
    setLoading(true);
    try {
      const data = await api.analyzeMeeting(meeting.id, { signal: controller.signal });
      if (!controller.signal.aborted && isMountedRef.current && !isEndingRef.current) {
        setAnalysis(data);
        setActiveTab('analysis');
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error generating analysis:', error);
        alert(error.message || 'Error generating analysis');
      }
    } finally {
      releaseRequestController(controller);
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const handleEndMeetingClick = async () => {
    cleanupMeetingActivity();
    await onEndMeeting();
  };

  return (
    <div className="meeting-view">
      <div className="meeting-header">
        <div className="meeting-title-section">
          <h2>{meeting.name}</h2>
          <p className="meeting-id">ID: {meeting.id}</p>
        </div>

        <div className="meeting-controls">
          <button
            className="btn btn-primary"
            onClick={handleGenerateAnalysis}
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Generate Analysis'}
          </button>
          <button
            className="btn btn-danger"
            onClick={handleEndMeetingClick}
          >
            {isRecording ? 'End Meeting' : 'Back to Dashboard'}
          </button>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'transcript' ? 'active' : ''}`}
          onClick={() => setActiveTab('transcript')}
        >
          Transcript ({transcript.length})
        </button>
        <button
          className={`tab ${activeTab === 'speakers' ? 'active' : ''}`}
          onClick={() => setActiveTab('speakers')}
        >
          Speakers ({speakers.length})
        </button>
        <button
          className={`tab ${activeTab === 'sentiment' ? 'active' : ''}`}
          onClick={() => setActiveTab('sentiment')}
        >
          Sentiment
        </button>
        <button
          className={`tab ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          Analysis
        </button>
        <button
          className={`tab ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab('query')}
        >
          Q&A
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
