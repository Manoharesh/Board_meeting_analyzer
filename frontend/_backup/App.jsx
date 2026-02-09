import React, { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';
import Dashboard from './pages/Dashboard';
import MeetingView from './pages/MeetingView';

const App = () => {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  // Load meetings on mount
  useEffect(() => {
    loadMeetings();
  }, []);

  // Update recording time
  useEffect(() => {
    if (!isRecording) return;
    
    const interval = setInterval(() => {
      setRecordingTime(prev => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isRecording]);

  const loadMeetings = async () => {
    try {
      const response = await fetch('/api/meeting/meetings/list/all');
      const data = await response.json();
      if (data.meetings) {
        setMeetings(data.meetings);
      }
    } catch (error) {
      console.error('Error loading meetings:', error);
    }
  };

  const handleStartMeeting = async (meetingName) => {
    try {
      const response = await fetch('/api/meeting/start?meeting_name=' + encodeURIComponent(meetingName));
      const data = await response.json();
      
      if (data.meeting_id) {
        setSelectedMeeting({
          id: data.meeting_id,
          name: meetingName,
          startTime: data.start_time,
          status: 'recording'
        });
        setIsRecording(true);
        setRecordingTime(0);
        setCurrentPage('meeting');
        loadMeetings();
      }
    } catch (error) {
      console.error('Error starting meeting:', error);
    }
  };

  const handleEndMeeting = async () => {
    try {
      const response = await fetch(`/api/meeting/end/${selectedMeeting.id}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      setIsRecording(false);
      setSelectedMeeting(null);
      setCurrentPage('dashboard');
      loadMeetings();
    } catch (error) {
      console.error('Error ending meeting:', error);
    }
  };

  const handleSelectMeeting = (meeting) => {
    setSelectedMeeting(meeting);
    setCurrentPage('meeting');
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>📊 Board Meeting Analyzer</h1>
        <div className="header-info">
          {isRecording && (
            <div className="recording-indicator">
              <span className="recording-dot"></span>
              Recording • {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
            </div>
          )}
        </div>
      </header>

      <nav className="app-nav">
        <button 
          className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          📋 Dashboard
        </button>
        {selectedMeeting && (
          <button 
            className={`nav-btn ${currentPage === 'meeting' ? 'active' : ''}`}
            onClick={() => setCurrentPage('meeting')}
          >
            🎙️ {selectedMeeting.name}
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
