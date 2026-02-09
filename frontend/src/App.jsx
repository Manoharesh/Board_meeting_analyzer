import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './pages/Dashboard';
import MeetingView from './pages/MeetingView';
import api from './services/api';

const normalizeMeeting = (meeting) => ({
  id: meeting.id || meeting.meeting_id,
  name: meeting.name || meeting.meeting_name || 'Untitled Meeting',
  startTime: meeting.startTime || meeting.start_time || null,
  status: meeting.status || (meeting.end_time ? 'completed' : 'active'),
  participants: Array.isArray(meeting.participants) ? meeting.participants : []
});

const App = () => {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  // Load meetings on mount.
  useEffect(() => {
    loadMeetings();
  }, []);

  // Update recording time.
  useEffect(() => {
    if (!isRecording) {
      return undefined;
    }

    const interval = setInterval(() => {
      setRecordingTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isRecording]);

  const loadMeetings = async () => {
    try {
      const data = await api.listMeetings();
      setMeetings(Array.isArray(data.meetings) ? data.meetings : []);
    } catch (error) {
      console.error('Error loading meetings:', error);
    }
  };

  const handleStartMeeting = async (meetingName, participants = []) => {
    try {
      const data = await api.startMeeting({ meetingName, participants });

      if (data.meeting_id) {
        setSelectedMeeting({
          id: data.meeting_id,
          name: data.meeting_name || meetingName,
          startTime: data.start_time,
          status: 'recording',
          participants: data.participants || []
        });
        setIsRecording(true);
        setRecordingTime(0);
        setCurrentPage('meeting');
        await loadMeetings();
      }
    } catch (error) {
      console.error('Error starting meeting:', error);
      alert(error.message || 'Failed to start meeting');
    }
  };

  const handleEndMeeting = async () => {
    if (!selectedMeeting?.id) {
      return;
    }

    const meetingId = selectedMeeting.id;
    const wasRecording = isRecording;

    // Stop UI recording state immediately so child cleanup runs right away.
    setIsRecording(false);
    setRecordingTime(0);

    if (!wasRecording) {
      setSelectedMeeting(null);
      setCurrentPage('dashboard');
      return;
    }

    try {
      await api.endMeeting(meetingId);
    } catch (error) {
      console.error('Error ending meeting:', error);
    } finally {
      setSelectedMeeting(null);
      setCurrentPage('dashboard');
      await loadMeetings();
    }
  };

  const handleSelectMeeting = (meeting) => {
    setSelectedMeeting(normalizeMeeting(meeting));
    setIsRecording(false);
    setRecordingTime(0);
    setCurrentPage('meeting');
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Board Meeting Analyzer</h1>
        <div className="header-info">
          {isRecording && (
            <div className="recording-indicator">
              <span className="recording-dot" />
              Recording - {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
            </div>
          )}
        </div>
      </header>

      <nav className="app-nav">
        <button
          className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          Dashboard
        </button>
        {selectedMeeting && (
          <button
            className={`nav-btn ${currentPage === 'meeting' ? 'active' : ''}`}
            onClick={() => setCurrentPage('meeting')}
          >
            {selectedMeeting.name}
          </button>
        )}
      </nav>

      <main className="app-main">
        {currentPage === 'dashboard' && (
          <Dashboard
            meetings={meetings}
            onStartMeeting={handleStartMeeting}
            onSelectMeeting={handleSelectMeeting}
          />
        )}

        {currentPage === 'meeting' && selectedMeeting && (
          <MeetingView
            meeting={selectedMeeting}
            onEndMeeting={handleEndMeeting}
            isRecording={isRecording}
          />
        )}
      </main>
    </div>
  );
};

export default App;
