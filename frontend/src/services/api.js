/**
 * API client service for Board Meeting Analyzer
 * Handles all communication with the backend API
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class MeetingAPIClient {
  // Meeting Management
  async startMeeting(meetingName, participants = []) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_name: meetingName, participants })
      });
      return await response.json();
    } catch (error) {
      console.error('Error starting meeting:', error);
      throw error;
    }
  }

  async endMeeting(meetingId) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/end/${meetingId}`, {
        method: 'POST'
      });
      return await response.json();
    } catch (error) {
      console.error('Error ending meeting:', error);
      throw error;
    }
  }

  async getMeeting(meetingId) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/${meetingId}`);
      return await response.json();
    } catch (error) {
      console.error('Error getting meeting:', error);
      throw error;
    }
  }

  async listMeetings() {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/meetings/list/all`);
      return await response.json();
    } catch (error) {
      console.error('Error listing meetings:', error);
      throw error;
    }
  }

  // Audio and Transcription
  async sendAudioChunk(meetingId, audioBlob) {
    try {
      const formData = new FormData();
      formData.append('chunk', audioBlob);

      const response = await fetch(`${API_BASE_URL}/meeting/audio-chunk/${meetingId}`, {
        method: 'POST',
        body: formData
      });
      return await response.json();
    } catch (error) {
      console.error('Error sending audio chunk:', error);
      throw error;
    }
  }

  async addTextChunk(meetingId, speaker, text) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_id: meetingId, speaker, text })
      });
      return await response.json();
    } catch (error) {
      console.error('Error adding text chunk:', error);
      throw error;
    }
  }

  // Transcripts
  async getTranscript(meetingId) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/transcript/${meetingId}`);
      return await response.json();
    } catch (error) {
      console.error('Error getting transcript:', error);
      throw error;
    }
  }

  // Analysis
  async analyzeMeeting(meetingId) {
    try {
      const response = await fetch(`${API_BASE_URL}/meeting/analysis/${meetingId}`);
      return await response.json();
    } catch (error) {
      console.error('Error analyzing meeting:', error);
      throw error;
    }
  }

  // Queries
  async queryByTopic(meetingId, topic) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/query/topic/${meetingId}?topic=${encodeURIComponent(topic)}`
      );
      return await response.json();
    } catch (error) {
      console.error('Error querying by topic:', error);
      throw error;
    }
  }

  async semanticQuery(meetingId, query) {
    try {
      const response = await fetch(`${API_BASE_URL}/query/semantic/${meetingId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      return await response.json();
    } catch (error) {
      console.error('Error in semantic query:', error);
      throw error;
    }
  }

  async askMeeting(meetingId, question) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/query/ask/${meetingId}?question=${encodeURIComponent(question)}`,
        { method: 'POST' }
      );
      return await response.json();
    } catch (error) {
      console.error('Error asking meeting question:', error);
      throw error;
    }
  }

  async getSpeakers(meetingId) {
    try {
      const response = await fetch(`${API_BASE_URL}/query/speakers/${meetingId}`);
      return await response.json();
    } catch (error) {
      console.error('Error getting speakers:', error);
      throw error;
    }
  }

  // Voice Enrollment
  async enrollSpeaker(speakerName, audioBlob) {
    try {
      const formData = new FormData();
      formData.append('speaker_name', speakerName);
      formData.append('audio_file', audioBlob);

      const response = await fetch(`${API_BASE_URL}/voice/enroll`, {
        method: 'POST',
        body: formData
      });
      return await response.json();
    } catch (error) {
      console.error('Error enrolling speaker:', error);
      throw error;
    }
  }

  async getEnrolledSpeakers() {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/speakers`);
      return await response.json();
    } catch (error) {
      console.error('Error getting enrolled speakers:', error);
      throw error;
    }
  }

  async getSpeakerInfo(speakerName) {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/speakers/${encodeURIComponent(speakerName)}`);
      return await response.json();
    } catch (error) {
      console.error('Error getting speaker info:', error);
      throw error;
    }
  }

  async removeSpeaker(speakerName) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/voice/speakers/${encodeURIComponent(speakerName)}`,
        { method: 'DELETE' }
      );
      return await response.json();
    } catch (error) {
      console.error('Error removing speaker:', error);
      throw error;
    }
  }

  async reenrollSpeaker(speakerName, audioBlob) {
    try {
      const formData = new FormData();
      formData.append('audio_file', audioBlob);

      const response = await fetch(
        `${API_BASE_URL}/voice/speakers/${encodeURIComponent(speakerName)}/re-enroll`,
        {
          method: 'POST',
          body: formData
        }
      );
      return await response.json();
    } catch (error) {
      console.error('Error re-enrolling speaker:', error);
      throw error;
    }
  }
}

// Export singleton instance
export default new MeetingAPIClient();
