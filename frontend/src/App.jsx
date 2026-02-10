import React, { useMemo, useState, useEffect } from 'react';
import './App.css';
import MeetingView from './pages/MeetingView';
import AppButton from './components/AppButton';
import AuroraBackground from './components/AuroraBackground';
import api from './services/api';

const parseParticipants = (participants) =>
  participants
    .split(',')
    .map((name) => name.trim())
    .filter(Boolean);

const normalizeMeeting = (meeting) => ({
  id: meeting.id || meeting.meeting_id,
  name: meeting.name || meeting.meeting_name || 'Untitled Meeting',
  startTime: meeting.startTime || meeting.start_time || null,
  status: meeting.status || (meeting.end_time ? 'completed' : 'active'),
  participants: Array.isArray(meeting.participants) ? meeting.participants : []
});

const formatMeetingTime = (value) => {
  if (!value) {
    return 'No date';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'No date';
  }

  return date.toLocaleString();
};

const App = () => {
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [showNewMeetingForm, setShowNewMeetingForm] = useState(false);
  const [meetingName, setMeetingName] = useState('');
  const [participants, setParticipants] = useState('');
  const [isStartingMeeting, setIsStartingMeeting] = useState(false);

  useEffect(() => {
    loadMeetings();
  }, []);

  useEffect(() => {
    if (!isRecording) {
      return undefined;
    }

    const interval = setInterval(() => {
      setRecordingTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isRecording]);

  const meetingsForSidebar = useMemo(() => {
    const normalized = (Array.isArray(meetings) ? meetings : []).map(normalizeMeeting);
    return normalized.sort((a, b) => {
      const first = a.startTime ? new Date(a.startTime).getTime() : 0;
      const second = b.startTime ? new Date(b.startTime).getTime() : 0;
      return second - first;
    });
  }, [meetings]);

  const loadMeetings = async () => {
    try {
      const data = await api.listMeetings();
      setMeetings(Array.isArray(data.meetings) ? data.meetings : []);
    } catch (error) {
      console.error('Error loading meetings:', error);
    }
  };

  const handleShowNewMeetingForm = () => {
    setShowNewMeetingForm(true);
    setSelectedMeeting(null);
    setMeetingName('');
    setParticipants('');
  };

  const handleCancelNewMeeting = () => {
    setShowNewMeetingForm(false);
    setMeetingName('');
    setParticipants('');
  };

  const handleStartMeeting = async (event) => {
    event.preventDefault();

    if (!meetingName.trim()) {
      alert('Please enter a meeting name');
      return;
    }

    setIsStartingMeeting(true);
    try {
      const data = await api.startMeeting({
        meetingName: meetingName.trim(),
        participants: parseParticipants(participants)
      });

      if (data.meeting_id) {
        setSelectedMeeting({
          id: data.meeting_id,
          name: data.meeting_name || meetingName.trim(),
          startTime: data.start_time,
          status: 'recording',
          participants: Array.isArray(data.participants) ? data.participants : []
        });
        setIsRecording(true);
        setRecordingTime(0);
        setShowNewMeetingForm(false);
        setMeetingName('');
        setParticipants('');
        await loadMeetings();
      }
    } catch (error) {
      console.error('Error starting meeting:', error);
      alert(error.message || 'Failed to start meeting');
    } finally {
      setIsStartingMeeting(false);
    }
  };

  const handleEndMeeting = async () => {
    if (!selectedMeeting?.id) {
      return;
    }

    const meetingId = selectedMeeting.id;
    const wasRecording = isRecording;

    setIsRecording(false);
    setRecordingTime(0);

    if (!wasRecording) {
      void loadMeetings();
      return;
    }

    try {
      return await api.endMeeting(meetingId);
    } catch (error) {
      console.error('Error ending meeting:', error);
    } finally {
      void loadMeetings();
    }
  };

  const handleSelectMeeting = (meeting) => {
    setSelectedMeeting(normalizeMeeting(meeting));
    setShowNewMeetingForm(false);
    setIsRecording(false);
    setRecordingTime(0);
  };

  return (
    <div className="app-shell">
      <AuroraBackground />
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="sidebar-header">
            <h1>Board Meeting Assistant</h1>
            <p>Conversation-first meeting workspace</p>
          </div>

          {isRecording && (
            <div className="sidebar-recording">
              <span className="recording-dot" />
              Live now {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
            </div>
          )}

          <AppButton
            className="btn-primary sidebar-new-meeting-btn"
            onClick={handleShowNewMeetingForm}
            disabled={isRecording}
          >
            New Meeting
          </AppButton>

          <div className="sidebar-meeting-list">
            {meetingsForSidebar.length > 0 ? (
              meetingsForSidebar.map((meeting) => (
                <button
                  key={meeting.id}
                  type="button"
                  className={`meeting-link ${selectedMeeting?.id === meeting.id && !showNewMeetingForm ? 'active' : ''}`}
                  onClick={() => handleSelectMeeting(meeting)}
                >
                  <span className="meeting-link-title">{meeting.name}</span>
                  <span className="meeting-link-time">{formatMeetingTime(meeting.startTime)}</span>
                </button>
              ))
            ) : (
              <p className="sidebar-empty">No meetings yet</p>
            )}
          </div>
        </aside>

        <main className="chat-main">
          {showNewMeetingForm ? (
            <section className="new-meeting-panel">
              <h2>Start a new meeting</h2>
              <p>Create a meeting and continue the conversation as it unfolds.</p>

              <form className="new-meeting-form" onSubmit={handleStartMeeting}>
                <label htmlFor="meeting-name">Meeting Name</label>
                <input
                  id="meeting-name"
                  type="text"
                  value={meetingName}
                  onChange={(event) => setMeetingName(event.target.value)}
                  placeholder="Quarterly board review"
                  autoFocus
                />

                <label htmlFor="meeting-participants">Participants (optional)</label>
                <input
                  id="meeting-participants"
                  type="text"
                  value={participants}
                  onChange={(event) => setParticipants(event.target.value)}
                  placeholder="Alex, Priya, Jordan"
                />

                <div className="new-meeting-actions">
                  <AppButton type="submit" className="btn-primary" disabled={isStartingMeeting}>
                    {isStartingMeeting ? 'Starting...' : 'Start Meeting'}
                  </AppButton>
                  <AppButton type="button" className="btn-secondary" onClick={handleCancelNewMeeting}>
                    Cancel
                  </AppButton>
                </div>
              </form>
            </section>
          ) : selectedMeeting ? (
            <MeetingView
              meeting={selectedMeeting}
              onEndMeeting={handleEndMeeting}
              isRecording={isRecording}
            />
          ) : (
            <section className="chat-empty-state">
              <h2>Select a meeting</h2>
              <p>Choose a meeting from the left or start a new one to begin.</p>
            </section>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
