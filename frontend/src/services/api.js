/**
 * API client service for Board Meeting Analyzer
 * Handles all communication with the backend API
 */

const API_BASE_URL = (process.env.REACT_APP_API_URL || '/api').replace(/\/+$/, '');

const buildUrl = (path) => `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

const parseResponse = async (response) => {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
};

const extractErrorMessage = (payload, fallback) => {
  if (!payload) {
    return fallback;
  }
  if (typeof payload === 'string') {
    return payload;
  }
  if (typeof payload === 'object') {
    return payload.detail || payload.message || payload.error || fallback;
  }
  return fallback;
};

const request = async (path, options = {}) => {
  const response = await fetch(buildUrl(path), options);
  const payload = await parseResponse(response);

  if (!response.ok) {
    const fallback = `Request failed (${response.status})`;
    throw new Error(extractErrorMessage(payload, fallback));
  }

  return payload;
};

class MeetingAPIClient {
  // Meeting Management
  async startMeeting(dataOrMeetingName, participantsArg = []) {
    const meetingName = typeof dataOrMeetingName === 'object'
      ? dataOrMeetingName?.meetingName
      : dataOrMeetingName;
    const participants = typeof dataOrMeetingName === 'object'
      ? dataOrMeetingName?.participants
      : participantsArg;

    if (!meetingName || !String(meetingName).trim()) {
      throw new Error('meetingName is required');
    }

    const payload = {
      meeting_name: String(meetingName).trim()
    };

    if (Array.isArray(participants) && participants.length > 0) {
      payload.participants = participants;
    }

    return request('/meeting/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }

  async endMeeting(meetingId, requestOptions = {}) {
    return request(`/meeting/end/${meetingId}`, {
      method: 'POST',
      ...requestOptions
    });
  }

  async getMeeting(meetingId) {
    return request(`/meeting/${meetingId}`);
  }

  async listMeetings() {
    return request('/meeting/meetings/list/all');
  }

  // Audio and Transcription
  async sendAudioChunk(meetingId, audioBlob, requestOptions = {}) {
    const formData = new FormData();
    formData.append('chunk', audioBlob, `chunk-${Date.now()}.webm`);
    return request(`/meeting/audio-chunk/${meetingId}`, {
      method: 'POST',
      body: formData,
      ...requestOptions
    });
  }

  async addTextChunk(meetingId, speaker, text) {
    return request('/meeting/chunk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meeting_id: meetingId, speaker, text })
    });
  }

  // Transcripts
  async getTranscript(meetingId, requestOptions = {}) {
    return request(`/meeting/transcript/${meetingId}`, requestOptions);
  }

  // Analysis
  async analyzeMeeting(meetingId, requestOptions = {}) {
    return request(`/meeting/analysis/${meetingId}`, requestOptions);
  }

  // Queries
  async queryByTopic(meetingId, topic) {
    return request(`/query/topic/${meetingId}?topic=${encodeURIComponent(topic)}`);
  }

  async semanticQuery(meetingId, query) {
    return request(`/query/semantic/${meetingId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
  }

  async askMeeting(meetingId, question) {
    return request(`/query/ask/${meetingId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
  }

  async getSpeakers(meetingId, requestOptions = {}) {
    return request(`/query/speakers/${meetingId}`, requestOptions);
  }

  // Voice Enrollment
  async enrollSpeaker(speakerName, audioBlob) {
    const formData = new FormData();
    formData.append('speaker_name', speakerName);
    formData.append('audio_file', audioBlob, `${speakerName || 'speaker'}.webm`);
    return request('/voice/enroll', {
      method: 'POST',
      body: formData
    });
  }

  async getEnrolledSpeakers() {
    return request('/voice/speakers');
  }

  async getSpeakerInfo(speakerName) {
    return request(`/voice/speakers/${encodeURIComponent(speakerName)}`);
  }

  async removeSpeaker(speakerName) {
    return request(`/voice/speakers/${encodeURIComponent(speakerName)}`, {
      method: 'DELETE'
    });
  }

  async reenrollSpeaker(speakerName, audioBlob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `${speakerName || 'speaker'}.webm`);
    return request(`/voice/speakers/${encodeURIComponent(speakerName)}/re-enroll`, {
      method: 'POST',
      body: formData
    });
  }
}

// Export singleton instance
const apiClient = new MeetingAPIClient();
export default apiClient;

