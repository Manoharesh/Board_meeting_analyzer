import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/MeetingView.css';
import AppButton from '../components/AppButton';
import LiveTranscript from '../components/LiveTranscript';
import api from '../services/api';

const makeMessageId = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const toList = (value) => (Array.isArray(value) ? value : []);

const buildInsightMessages = (analysis) => {
  if (!analysis || typeof analysis !== 'object') {
    return [];
  }

  const messages = [];
  const summary = typeof analysis.summary === 'string' ? analysis.summary.trim() : '';
  const keyPoints = toList(analysis.key_points).filter(Boolean);
  const decisions = toList(analysis.decisions)
    .map((decision) => decision?.description)
    .filter(Boolean);
  const nextSteps = toList(analysis.action_items)
    .map((item) => {
      const description = item?.description || '';
      const owner = item?.owner ? `Owner: ${item.owner}` : '';
      const dueDate = item?.due_date ? `Due: ${item.due_date}` : '';
      const details = [owner, dueDate].filter(Boolean).join(' | ');
      return details ? `${description} (${details})` : description;
    })
    .filter(Boolean);

  if (summary) {
    messages.push({
      id: makeMessageId('insight-summary'),
      role: 'assistant',
      isInsight: true,
      title: 'Summary',
      body: summary
    });
  }

  if (keyPoints.length > 0) {
    messages.push({
      id: makeMessageId('insight-highlights'),
      role: 'assistant',
      isInsight: true,
      title: 'Highlights',
      items: keyPoints
    });
  }

  if (decisions.length > 0) {
    messages.push({
      id: makeMessageId('insight-decisions'),
      role: 'assistant',
      isInsight: true,
      title: 'Decisions',
      items: decisions
    });
  }

  if (nextSteps.length > 0) {
    messages.push({
      id: makeMessageId('insight-next-steps'),
      role: 'assistant',
      isInsight: true,
      title: 'Next Steps',
      items: nextSteps
    });
  }

  return messages;
};

const chooseRecorderMimeType = () => {
  if (typeof window === 'undefined' || typeof window.MediaRecorder === 'undefined') {
    return '';
  }

  const options = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus'
  ];

  return options.find((type) => MediaRecorder.isTypeSupported(type)) || '';
};

const MeetingView = ({ meeting, onEndMeeting, isRecording }) => {
  const [transcript, setTranscript] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [isRefreshingInsights, setIsRefreshingInsights] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isChatReady, setIsChatReady] = useState(true);
  const [isNoAudioTimeout, setIsNoAudioTimeout] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const noAudioTimeoutRef = useRef(null);
  const inFlightControllersRef = useRef(new Set());
  const isMountedRef = useRef(true);
  const chunkUploadQueueRef = useRef([]);
  const chunkUploadInFlightRef = useRef(false);
  const meetingDataRequestInFlightRef = useRef(false);
  const transcriptThreadRef = useRef(null);
  const endOfThreadRef = useRef(null);

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

  const clearPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const flushAudioQueue = useCallback(async () => {
    if (chunkUploadInFlightRef.current || !meeting?.id) {
      return;
    }

    chunkUploadInFlightRef.current = true;
    try {
      while (chunkUploadQueueRef.current.length > 0 && isMountedRef.current) {
        const audioBlob = chunkUploadQueueRef.current.shift();
        if (!audioBlob || audioBlob.size === 0) {
          console.warn('[Audio] Skipping empty audio blob');
          continue;
        }

        console.log(`[Audio] Uploading chunk: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
        try {
          const result = await api.sendAudioChunk(meeting.id, audioBlob);
          console.log('[Audio] Upload success:', result);

          if (result.status === 'audio detected' || result.status === 'ignored' || result.status === 'chunk stored') {
            setIsNoAudioTimeout(false);
            if (noAudioTimeoutRef.current) {
              clearTimeout(noAudioTimeoutRef.current);
              noAudioTimeoutRef.current = null;
            }
          }
        } catch (error) {
          console.error('[Audio] Upload error:', error);
        }
      }
    } finally {
      chunkUploadInFlightRef.current = false;
    }
  }, [meeting?.id]);

  const stopAudioCapture = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      if (recorder.state !== 'inactive') {
        const stopPromise = new Promise((resolve) => {
          const handleStop = () => {
            recorder.removeEventListener('stop', handleStop);
            resolve();
          };
          recorder.addEventListener('stop', handleStop);
        });

        try {
          recorder.requestData();
        } catch (error) {
          console.error('Error requesting final audio chunk:', error);
        }

        recorder.stop();
        await stopPromise;
      }

      recorder.ondataavailable = null;
      recorder.onerror = null;
    }
    mediaRecorderRef.current = null;

    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    await flushAudioQueue();
  }, [flushAudioQueue]);

  const loadMeetingData = useCallback(async () => {
    if (meetingDataRequestInFlightRef.current) {
      return;
    }

    meetingDataRequestInFlightRef.current = true;
    const controller = createRequestController();
    try {
      const [transcriptData, meetingData] = await Promise.all([
        api.getTranscript(meeting.id, { signal: controller.signal }),
        api.getMeeting(meeting.id, { signal: controller.signal })
      ]);

      if (controller.signal.aborted || !isMountedRef.current) {
        return;
      }

      setTranscript(Array.isArray(transcriptData.transcript) ? transcriptData.transcript : []);

      const transcriptionStatus = meetingData?.transcription_status || transcriptData?.transcription_status;
      const currentlyTranscribing = transcriptionStatus === 'processing' || transcriptionStatus === 'queued';
      setIsTranscribing(currentlyTranscribing);
      setIsChatReady(true);
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error loading meeting data:', error);
      }
    } finally {
      meetingDataRequestInFlightRef.current = false;
      releaseRequestController(controller);
    }
  }, [createRequestController, meeting.id, releaseRequestController]);

  const startAudioCapture = useCallback(async () => {
    if (!meeting?.id || isEnding) {
      return;
    }

    const existingRecorder = mediaRecorderRef.current;
    if (existingRecorder && existingRecorder.state === 'recording') {
      return;
    }

    try {
      console.log('[Audio] Starting microphone capture...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;
      console.log('[Audio] Stream active tracks:', stream.getAudioTracks().map(t => t.label));

      const mimeType = chooseRecorderMimeType();
      console.log('[Audio] Using MimeType:', mimeType);

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (event) => {
        console.log(`[Audio] Data available: ${event.data ? event.data.size : 0} bytes`);
        if (event.data && event.data.size > 0) {
          chunkUploadQueueRef.current.push(event.data);
          void flushAudioQueue();
        }
      };

      mediaRecorder.onstart = () => {
        console.log('[Audio] MediaRecorder started, state:', mediaRecorder.state);
        setIsNoAudioTimeout(false);
        noAudioTimeoutRef.current = setTimeout(() => {
          console.error('[Audio] No real audio detected within 5 seconds');
          setIsNoAudioTimeout(true);
        }, 5000);
      };

      mediaRecorder.onerror = (event) => {
        console.error('[Audio] MediaRecorder error:', event.error || event);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(2000);
      setIsChatReady(true);
    } catch (error) {
      console.error('[Audio] Error starting microphone capture:', error);
      setIsChatReady(true);
    }
  }, [flushAudioQueue, isEnding, meeting?.id]);

  const refreshInsights = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsRefreshingInsights(true);
    }

    const controller = createRequestController();
    try {
      const data = await api.analyzeMeeting(meeting.id, { signal: controller.signal });
      if (!controller.signal.aborted && isMountedRef.current) {
        setAnalysis(data);
        setMessages((previous) => {
          const preserved = previous.filter((item) => !item.isInsight);
          const generated = buildInsightMessages(data);

          if (generated.length === 0) {
            generated.push({
              id: makeMessageId('insight-empty'),
              role: 'assistant',
              isInsight: true,
              title: 'Summary',
              body: 'There is not enough information yet to produce a reliable summary.'
            });
          }

          return [...preserved, ...generated];
        });
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error refreshing insights:', error);
      }
    } finally {
      releaseRequestController(controller);
      if (isMountedRef.current && showLoading) {
        setIsRefreshingInsights(false);
      }
    }
  }, [createRequestController, meeting.id, releaseRequestController]);

  useEffect(() => {
    setAnalysis(null);
    setTranscript([]);
    setPrompt('');
    setIsEnding(false);
    setIsTranscribing(false);
    setIsChatReady(Boolean(meeting?.id));
    chunkUploadQueueRef.current = [];
    setMessages([
      {
        id: makeMessageId('intro'),
        role: 'assistant',
        title: 'Ready',
        body: 'Ask anything about this meeting and I will answer using the discussion context.'
      }
    ]);
  }, [meeting?.id]);

  useEffect(() => {
    clearPolling();
    void loadMeetingData();
    void refreshInsights(false);
    pollingIntervalRef.current = setInterval(() => {
      void loadMeetingData();
    }, 3000);

    return () => clearPolling();
  }, [clearPolling, loadMeetingData, refreshInsights]);

  useEffect(() => {
    if (isRecording && !isEnding) {
      void startAudioCapture();
      return;
    }

    void stopAudioCapture();
  }, [isEnding, isRecording, startAudioCapture, stopAudioCapture]);

  useEffect(() => {
    endOfThreadRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking, isRefreshingInsights, isTranscribing]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      clearPolling();
      abortInFlightRequests();
      void stopAudioCapture();
    };
  }, [abortInFlightRequests, clearPolling, stopAudioCapture]);

  const handlePromptSubmit = async (event) => {
    event.preventDefault();
    const question = prompt.trim();
    if (!question || !isChatReady) {
      return;
    }

    setMessages((previous) => [
      ...previous,
      {
        id: makeMessageId('user'),
        role: 'user',
        body: question
      }
    ]);
    setPrompt('');

    const controller = createRequestController();
    setIsAsking(true);
    try {
      const data = await api.semanticQuery(meeting.id, question, { signal: controller.signal });
      if (!controller.signal.aborted && isMountedRef.current) {
        const supportNotes = toList(data.relevant_chunks)
          .slice(0, 3)
          .map((chunk) => {
            const speaker = chunk?.speaker ? `${chunk.speaker}: ` : '';
            const text = typeof chunk?.text === 'string' ? chunk.text.trim() : '';
            return `${speaker}${text}`.trim();
          })
          .filter(Boolean);

        setMessages((previous) => [
          ...previous,
          {
            id: makeMessageId('assistant'),
            role: 'assistant',
            title: 'Answer',
            body: typeof data.answer === 'string' && data.answer.trim()
              ? data.answer.trim()
              : 'I could not find enough detail to answer that yet.',
            items: supportNotes.length > 0 ? supportNotes : null
          }
        ]);
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error processing prompt:', error);
        if (isMountedRef.current) {
          setMessages((previous) => [
            ...previous,
            {
              id: makeMessageId('assistant-error'),
              role: 'assistant',
              title: 'Unable to answer right now',
              body: error.message || 'Please try asking again in a moment.'
            }
          ]);
        }
      }
    } finally {
      releaseRequestController(controller);
      if (isMountedRef.current) {
        setIsAsking(false);
      }
    }
  };

  const handleEndMeetingClick = async () => {
    if (isEnding) {
      return;
    }

    setIsEnding(true);
    setIsRefreshingInsights(false);
    setIsTranscribing(true);
    setIsChatReady(true);

    try {
      await stopAudioCapture();
      await onEndMeeting();
      await loadMeetingData();
      void refreshInsights(false);
    } catch (error) {
      console.error('Error ending meeting:', error);
    } finally {
      if (isMountedRef.current) {
        setIsEnding(false);
      }
    }
  };

  return (
    <section className="meeting-view">
      <header className="meeting-view-header">
        <div>
          <h2>{meeting.name}</h2>
          <p>
            {isRecording ? 'Live meeting in progress' : 'Meeting ready for conversation'}
            {transcript.length > 0 ? ` | ${transcript.length} notes captured` : ''}
            {isTranscribing ? ' | Transcription in progress' : ''}
          </p>
          {isNoAudioTimeout && (
            <div className="audio-alert-banner">
              ⚠️ No audio detected. Please check your microphone settings.
            </div>
          )}
        </div>

        <div className="meeting-view-actions">
          <AppButton
            className="btn-secondary"
            onClick={() => void refreshInsights(true)}
            disabled={isRefreshingInsights || isEnding}
          >
            {isRefreshingInsights ? 'Refreshing...' : 'Refresh Summary'}
          </AppButton>
          {isRecording && (
            <AppButton className="btn-danger" onClick={handleEndMeetingClick} disabled={isEnding}>
              {isEnding ? 'Ending...' : 'End Meeting'}
            </AppButton>
          )}
        </div>
      </header>

      <div className="meeting-content">
        <div className="conversation-thread" aria-live="polite">
          {messages.map((message) => (
            <article key={message.id} className={`message message-${message.role}`}>
              {message.title && <h3>{message.title}</h3>}
              {message.body && <p>{message.body}</p>}
              {Array.isArray(message.items) && message.items.length > 0 && (
                <ul>
                  {message.items.map((item) => (
                    <li key={`${message.id}-${item}`}>{item}</li>
                  ))}
                </ul>
              )}
            </article>
          ))}

          {isAsking && (
            <article className="message message-assistant message-loading">
              <p>Thinking...</p>
            </article>
          )}

          {!analysis && !isRefreshingInsights && messages.length === 1 && (
            <article className="message message-assistant">
              <p>I am waiting for enough content to generate a summary.</p>
            </article>
          )}

          <div ref={endOfThreadRef} />
        </div>

        {/* Live Transcript Sidebar/Section */}
        <aside className="meeting-sidebar">
          <LiveTranscript transcript={transcript} />
        </aside>
      </div>

      <form className="prompt-bar" onSubmit={handlePromptSubmit}>
        <input
          type="text"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Ask about this meeting..."
          disabled={isAsking || !isChatReady}
        />
        <AppButton
          type="submit"
          className="btn-primary"
          disabled={isAsking || !prompt.trim() || !isChatReady}
        >
          {isAsking ? 'Sending...' : 'Send'}
        </AppButton>
      </form>
    </section>
  );
};

export default MeetingView;
