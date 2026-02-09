# Board Meeting Analyzer - Setup & Installation Guide

## 🎯 Features Overview

- **Real-time Transcription**: Automatic speech-to-text conversion with speaker identification
- **Speaker Enrollment**: Register voices (10-20 sec) to automatically identify speakers by name
- **Speaker Diarization**: Automatically chunks audio by speakers and identifies unique voices
- **Sentiment Analysis**: Tracks sentiment and emotion per speaker with timeline visualization
- **AI Meeting Summary**: Auto-generated summaries and key points extraction
- **Decision & Action Items**: Automatic extraction from transcript
- **Meeting Q&A**: Ask questions using natural language about meeting content
- **Meeting Metadata**: Tracks meeting ID, date, time, and participants

## 📋 Prerequisites

- Python 3.8+ (Backend)
- Node.js 14+ (Frontend)
- Microphone access for audio input
- 4GB+ RAM recommended
- Optional: Ollama for local LLM (or use OpenAI/Azure)

## 🚀 Quick Start

### 1. Backend Setup

#### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

Key configurations:
- `STT_ENGINE`: Choose between 'google', 'whisper', or 'azure'
- `LLM_ENGINE`: Choose between 'ollama', 'openai', or 'azure'
- `LLM_MODEL`: Model name (e.g., 'llama3' for Ollama, 'gpt-4' for OpenAI)

#### Step 3: Install Optional LLM (Ollama)

For local LLM execution without API costs:

```bash
# Download and install Ollama from https://ollama.ai
# Start Ollama service:
ollama serve

# In another terminal, pull the model:
ollama pull llama3
```

#### Step 4: Run Backend Server

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend will run at `http://localhost:3000`

## 📡 API Endpoints

### Meeting Management
- `POST /api/meeting/start` - Start a new meeting
- `POST /api/meeting/end/{meeting_id}` - End a meeting
- `POST /api/meeting/audio-chunk/{meeting_id}` - Process audio chunk
- `POST /api/meeting/chunk` - Add text chunk directly
- `GET /api/meeting/analysis/{meeting_id}` - Get meeting analysis
- `GET /api/meeting/transcript/{meeting_id}` - Get transcript
- `GET /api/meeting/{meeting_id}` - Get meeting data
- `GET /api/meeting/meetings/list/all` - List all meetings

### Queries
- `GET /api/query/topic/{meeting_id}?topic=...` - Topic search
- `POST /api/query/semantic/{meeting_id}` - Smart Q&A
- `POST /api/query/ask/{meeting_id}` - Ask question
- `GET /api/query/speakers/{meeting_id}` - Get speakers

### Voice Enrollment
- `POST /api/voice/enroll` - Enroll speaker voice
- `GET /api/voice/speakers` - List enrolled speakers
- `GET /api/voice/speakers/{speaker_name}` - Get speaker info
- `DELETE /api/voice/speakers/{speaker_name}` - Remove speaker
- `POST /api/voice/speakers/{speaker_name}/re-enroll` - Re-enroll speaker

## 💥 Usage Examples

### 1. Start a Meeting

```bash
curl -X POST "http://localhost:8000/api/meeting/start?meeting_name=Board%20Meeting&participants=John&participants=Sarah"
```

Response:
```json
{
  "status": "meeting started",
  "meeting_id": "20240209_140530_Board_Meeting",
  "meeting_name": "Board Meeting",
  "start_time": "2024-02-09T14:05:30.123456",
  "participants": ["John", "Sarah"]
}
```

### 2. Enroll a Speaker

```bash
curl -X POST "http://localhost:8000/api/voice/enroll" \
  -F "speaker_name=John" \
  -F "audio_file=@voice_sample.wav"
```

### 3. Send Audio Chunk

```bash
curl -X POST "http://localhost:8000/api/meeting/audio-chunk/20240209_140530_Board_Meeting" \
  -F "chunk=@audio_segment.wav"
```

### 4. Ask Question About Meeting

```bash
curl -X POST "http://localhost:8000/api/query/semantic/20240209_140530_Board_Meeting" \
  -H "Content-Type: application/json" \
  -d '{"query": "What were the key decisions made?"}'
```

### 5. Generate Analysis

```bash
curl -X GET "http://localhost:8000/api/meeting/analysis/20240209_140530_Board_Meeting"
```

## 🔧 Configuration Details

### STT Engine Options

**Google Speech Recognition** (Recommended for quick start)
- No API key required
- Works locally
- Requires `SpeechRecognition` library

**OpenAI Whisper**
- Offline capable
- Most accurate
- Requires `openai-whisper` library
- Can use local model

**Azure Speech Services**
- Enterprise-grade
- Real-time streaming
- Requires Azure subscription and credentials

### LLM Engine Options

**Ollama** (Recommended for local use)
- Free and open-source
- No privacy concerns
- Runs locally
- Models: llama3, mistral, etc.

**OpenAI**
- Most capable
- Requires API key and credits
- Models: gpt-4, gpt-3.5-turbo

**Azure OpenAI**
- Enterprise option
- Requires Azure subscription

## 📊 Data Structure

### Meeting Metadata
```python
{
  "meeting_id": "20240209_140530_Board_Meeting",
  "meeting_name": "Board Meeting",
  "start_time": "2024-02-09T14:05:30",
  "end_time": "2024-02-09T15:30:00",
  "participants": ["John", "Sarah", "Mike"]
}
```

### Transcript Entry
```python
{
  "speaker_name": "John",
  "speaker_id": "John",
  "text": "We need to focus on Q4 goals...",
  "timestamp": 120.5,
  "duration": 5.2,
  "sentiment": "positive"
}
```

### Analysis Result
```python
{
  "summary": "The board discussed Q4 objectives...",
  "key_points": ["Focus on cost reduction", "Expand market presence"],
  "decisions": [
    {
      "id": "decision_0",
      "description": "Approved new marketing budget",
      "owner": "Sarah",
      "status": "decided"
    }
  ],
  "action_items": [
    {
      "id": "action_0",
      "description": "Prepare Q4 financial report",
      "owner": "Mike",
      "due_date": "2024-02-16",
      "priority": "high"
    }
  ],
  "sentiment_breakdown": {
    "John": {
      "overall_score": 0.45,
      "positive_count": 3,
      "negative_count": 1,
      "neutral_count": 2
    }
  }
}
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### API Testing with FastAPI Docs

1. Start the server
2. Visit `http://localhost:8000/docs` (Swagger UI)
3. Test endpoints directly in the interface

## 🐛 Troubleshooting

### Microphone Issues
- Check browser permissions (Chrome: Settings → Privacy → Site Settings → Mic)
- Ensure microphone is connected and recognized by OS
- Test with: `navigator.mediaDevices.enumerateDevices()` in browser console

### LLM Not Responding
- Check Ollama is running: `curl http://localhost:11434/api/version`
- Verify model is installed: `ollama list`
- Check API key if using OpenAI/Azure

### STT Errors
- Ensure audio format is WAV, 16-bit, 16kHz mono
- Check microphone audio levels
- Verify STT engine credentials if needed

### CORS Issues
- Update `CORS_ORIGINS` in `.env`
- Restart backend server

## 📈 Performance Tips

1. **Use Ollama locally** for better privacy and lower latency
2. **Optimize audio quality** - clear, 16kHz mono works best
3. **Batch queries** - combine multiple questions to reduce API calls
4. **Archive old meetings** - periodically move to database for storage

## 🔐 Security Considerations

1. **API Keys**: Store in `.env`, never commit to git
2. **Audio Data**: Runs locally, not stored by default
3. **Database**: Use encrypted database for production
4. **CORS**: Restrict origins in production
5. **Rate Limiting**: Add rate limiting for API endpoints

## 📚 Advanced Usage

### Custom Sentiment Emotions
Edit `app/config.py`:
```python
SENTIMENT_EMOTIONS = [
    'confidence', 'concern', 'disagreement', ...
]
```

### Database Integration
Currently uses in-memory storage. For production:

```bash
pip install sqlalchemy postgresql  # or other DB
# Update DATABASE_URL and models
```

### Speaker Embeddings
For better speaker identification, consider:
- PyAnnote.audio (state-of-the-art diarization)
- Resemblyzer (speaker embeddings)
- SpeechBrain

## 📝 Development

### File Structure
```
backend/
├── app/
│   ├── ai/              # AI/ML modules
│   ├── api/             # API routes
│   ├── audio/           # Audio processing
│   ├── memory/          # Data storage
│   ├── models/          # Data schemas
│   ├── transcription/   # STT
│   ├── config.py        # Configuration
│   └── main.py          # FastAPI app
├── requirements.txt
└── tests/

frontend/
├── components/          # React components
├── pages/              # Page components
├── services/           # API client
├── styles/             # CSS files
├── App.jsx
└── package.json
```

### Adding New AI Modules
1. Create module in `app/ai/`
2. Use `call_llm()` for LLM integration
3. Add route in `app/api/`

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Better speaker diarization
- Real-time sentiment visualization
- Video transcription support
- Multi-language support
- Database integration

## 📄 License

MIT License - See LICENSE file

## 🆘 Support

For issues and questions:
1. Check troubleshooting section
2. Review API documentation at `/docs`
3. Check logs in `./logs/analyzer.log`
4. Create an issue with error details

---

**Version**: 2.0.0  
**Last Updated**: February 2024
