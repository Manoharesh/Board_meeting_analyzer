import React, { useState } from 'react';
import '../styles/Dashboard.css';

const parseParticipants = (participants) =>
  participants
    .split(',')
    .map((name) => name.trim())
    .filter(Boolean);

const Dashboard = ({ meetings, onStartMeeting, onSelectMeeting }) => {
  const [meetingName, setMeetingName] = useState('');
  const [participants, setParticipants] = useState('');
  const [showNewMeetingForm, setShowNewMeetingForm] = useState(false);

  const handleStartMeeting = (e) => {
    e.preventDefault();
    if (!meetingName.trim()) {
      alert('Please enter a meeting name');
      return;
    }

    onStartMeeting(meetingName.trim(), parseParticipants(participants));
    setMeetingName('');
    setParticipants('');
    setShowNewMeetingForm(false);
  };

  const formatDateTime = (isoString) => {
    if (!isoString) {
      return 'N/A';
    }
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className="dashboard">
      <section className="welcome-section">
        <h2>Welcome to Board Meeting Analyzer</h2>
        <p>Intelligent transcription, analysis, and Q&A for your board meetings</p>

        {!showNewMeetingForm ? (
          <button
            className="btn btn-primary"
            onClick={() => setShowNewMeetingForm(true)}
          >
            Start New Meeting
          </button>
        ) : (
          <form className="new-meeting-form" onSubmit={handleStartMeeting}>
            <div className="form-group">
              <label>Meeting Name</label>
              <input
                type="text"
                value={meetingName}
                onChange={(e) => setMeetingName(e.target.value)}
                placeholder="Board Meeting - Q4 2024"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Participants (optional)</label>
              <input
                type="text"
                value={participants}
                onChange={(e) => setParticipants(e.target.value)}
                placeholder="John, Sarah, Mike"
              />
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary">
                Start Recording
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowNewMeetingForm(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="meetings-section">
        <h3>Recent Meetings</h3>

        {Array.isArray(meetings) && meetings.length > 0 ? (
          <div className="meetings-grid">
            {meetings.map((meeting) => {
              const meetingId = meeting.meeting_id || meeting.id;
              const participantsList = Array.isArray(meeting.participants) ? meeting.participants : [];

              return (
                <div
                  key={meetingId}
                  className="meeting-card"
                >
                  <div className="meeting-header">
                    <h4>{meeting.name || meeting.meeting_name || meetingId}</h4>
                    <span className="meeting-date">
                      {formatDateTime(meeting.start_time || meeting.startTime)}
                    </span>
                  </div>

                  <div className="meeting-stats">
                    <div className="stat">
                      <span className="stat-label">Segments</span>
                      <span className="stat-value">{meeting.chunk_count || 0}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Participants</span>
                      <span className="stat-value">{participantsList.length || 'N/A'}</span>
                    </div>
                  </div>

                  <div className="meeting-participants">
                    {participantsList.length > 0 && (
                      <>
                        <span className="label">Participants: </span>
                        <span>{participantsList.join(', ')}</span>
                      </>
                    )}
                  </div>

                  <button
                    className="btn btn-secondary"
                    onClick={() => onSelectMeeting(meeting)}
                  >
                    View Details
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="no-meetings">
            <p>No meetings yet. Start one to begin.</p>
          </div>
        )}
      </section>

      <section className="features-section">
        <h3>Features</h3>
        <div className="features-grid">
          <div className="feature">
            <div className="feature-icon">TR</div>
            <h4>Real-time Transcription</h4>
            <p>Automatic speech-to-text conversion with speaker identification</p>
          </div>

          <div className="feature">
            <div className="feature-icon">SP</div>
            <h4>Speaker Enrollment</h4>
            <p>Register voices to automatically identify speakers by name</p>
          </div>

          <div className="feature">
            <div className="feature-icon">SE</div>
            <h4>Sentiment Analysis</h4>
            <p>Track sentiment and emotion across all speakers</p>
          </div>

          <div className="feature">
            <div className="feature-icon">SU</div>
            <h4>Smart Summary</h4>
            <p>AI-generated summaries and key points extraction</p>
          </div>

          <div className="feature">
            <div className="feature-icon">AI</div>
            <h4>Action Items</h4>
            <p>Automatic extraction of decisions and action items</p>
          </div>

          <div className="feature">
            <div className="feature-icon">QA</div>
            <h4>Meeting Q&A</h4>
            <p>Ask questions about the meeting content</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
