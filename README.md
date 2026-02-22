# MeetMind

## 1. Project Title

MeetMind
Prototype codename in this repo: **AI Board Meeting Analyzer**

## 2. One-line Tagline

Turn meetings from fleeting conversations into durable, queryable organizational memory.

## 3. Vision

MeetMind is building an autonomous meeting intelligence system that joins meetings, listens in real time, converts speech into structured knowledge, and makes that knowledge searchable long after the call ends.

The product vision is not "better notes."
It is a memory layer for teams: decisions, commitments, context, and rationale captured as institutional knowledge.

## 4. Deep Problem Statement

Meetings are where modern teams make decisions, surface risks, negotiate priorities, and commit to action. Yet the output of those meetings is mostly lost.

Operationally, the failure is obvious:

- Decisions are made but not reliably documented.
- Action items are implied, not assigned.
- Teams re-discuss topics because prior context is hard to recover.
- New team members cannot reconstruct why a decision was made.
- Leadership lacks an auditable trail from discussion to execution.

Psychologically, the failure is worse:

- People assume "someone else captured that."
- Participants multitask and miss nuance.
- Late joiners interrupt flow and create recap tax.
- Long recordings become graveyards of context nobody re-watches.
- Human memory distorts details, ownership, and intent over time.

The result is predictable:

- Missed tasks
- Accountability gaps
- Knowledge silos
- Onboarding drag
- Decision traceability failures
- Slower execution despite more meetings

Teams generate knowledge every day. Most of it evaporates.

## 5. Why Existing Solutions Fail

Current tools usually solve only one layer:

- Recording tools preserve raw media, not structured knowledge.
- Transcript tools produce text dumps, not decision intelligence.
- Note apps depend on manual discipline during high-cognitive-load conversations.
- Summary bots provide snapshots, not a persistent, queryable memory graph.
- Search is often keyword-only and weak on intent, ownership, and rationale.

The core gap: no system converts live conversation into durable, structured, and retrievable organizational memory.

## 6. Our Solution

MeetMind creates an end-to-end meeting intelligence pipeline:

- Capture live meeting audio
- Transcribe continuously
- Extract decisions, action items, and key signals
- Persist structured outputs
- Generate concise summaries
- Enable natural-language retrieval over historical meetings

This turns meetings into a searchable system of record, not a one-time event.

## 7. What Exists Today (Prototype Capabilities - Based on This Repo)

This repository currently implements a local prototype, not the full autonomous platform.

Implemented now:

- FastAPI backend with Socket.IO streaming events
- Start/stop meeting session endpoints
- Local audio capture from default microphone (PyAudio)
- Voice activity detection (webrtcvad)
- Real-time chunk transcription via faster-whisper (tiny model)
- LLM-based sentiment analysis and decision/action-item extraction via local Ollama (llama3 with mistral fallback)
- Meeting/session persistence in SQLite (`board_meetings.db`) via SQLAlchemy
- Summary generation endpoint per meeting
- PDF export of meeting transcript and extracted decisions
- Simple static frontend (`index.html`) for live transcript + meeting list + summary/export actions

Current prototype constraints:

- No Google Meet auto-join yet
- No conferencing platform integrations yet
- No production auth, RBAC, or tenancy model
- Speaker diarization is scaffolded but disabled in active flow (default speaker placeholder)
- No vector search or cross-meeting semantic retrieval yet
- No assignment/closure workflow for action items yet
- Local-first architecture, not cloud deployment-ready

## 8. What We Are Building During This Hackathon

Hackathon scope is to prove the core wedge with a tighter end-to-end flow:

- Meeting-link based autonomous session kickoff (initial Google Meet path)
- Reliable real-time transcription + structured extraction in one pipeline
- Explicit decision and action-item objects with ownership fields
- Query-first meeting memory interface ("What did we decide about X?")
- Stronger meeting timeline view with citations to transcript segments
- Consent and participation signaling built into session lifecycle

Hackathon goal: demonstrate a credible product loop from conversation to persistent, queryable intelligence.

## 9. Target Users

Primary user segments:

- Startup founders and leadership teams running frequent decision-heavy meetings
- Chiefs of Staff and program leads responsible for follow-through
- Product and engineering managers coordinating cross-functional execution
- RevOps, customer success, and account teams that need decision traceability
- Compliance-sensitive teams that require auditable meeting records

## 10. Real Use Cases

- Board and leadership meetings: capture strategic decisions and assigned owners instantly.
- Product reviews: extract scope changes, blockers, and deadlines from discussion.
- Customer escalation calls: retain commitments and rationale with searchable context.
- Weekly operations standups: auto-track recurring blockers and unresolved items.
- New hire onboarding: query prior meeting history to understand "why" behind current plans.
- Cross-timezone collaboration: late joiners recover context without interrupting live flow.

## 11. How It Works (Technical Architecture Overview)

```text
[Local Audio Input]
      |
      v
[PyAudio Capture] -> [WebRTC VAD]
      |
      v
[5s Audio Chunks]
      |
      v
[Faster-Whisper Transcription]
      |
      +--------------------------+
      |                          |
      v                          v
[Sentiment Analysis]      [Decision/Action Extraction]
        (Ollama)                 (Ollama)
      |                          |
      +------------+-------------+
                   v
        [SQLite Persistence]
                   |
        +----------+-----------+
        |                      |
        v                      v
 [Socket.IO Live Feed]   [Summary/PDF APIs]
        |                      |
        v                      v
 [Browser UI]          [Exported Reports]
```

## 12. Tech Stack

| Layer | Current Prototype |
| --- | --- |
| API | FastAPI |
| Real-time transport | Socket.IO |
| Audio capture | PyAudio |
| Speech activity filter | webrtcvad |
| Transcription | faster-whisper |
| LLM analysis | Ollama (llama3, mistral fallback) |
| Persistence | SQLite + SQLAlchemy |
| Reporting | ReportLab (PDF export) |
| Frontend | Static HTML/CSS/JS |

## 13. Differentiation / Competitive Advantage

- Memory-first architecture: designed around persistent knowledge, not just transcription.
- Structured intelligence output: decisions and actions as data objects, not only prose summaries.
- Real-time + retrospective value: useful during the meeting and after.
- Local-first prototype path: fast iteration loop with privacy-friendly defaults.
- Clear enterprise expansion path: platform integrations, policy controls, auditability, multi-tenant architecture.

## 14. Privacy & Consent Model

Design principles:

- Explicit participant notice before capture
- Consent-aware join behavior
- Role-based access to transcripts and summaries
- Configurable retention and deletion policies
- Encryption and auditable access trails in production architecture

Prototype reality in this repo:

- Runs locally
- Stores meeting artifacts in local SQLite and local PDF exports
- Does not yet implement full consent workflow, identity, or policy enforcement

## 15. Monetization Strategy

Planned model:

- Per-host subscription for core meeting intelligence
- Usage-based processing for transcription/analysis minutes
- Team plan with shared memory/search and integrations
- Enterprise tier for compliance controls, SSO, governance, custom retention, and private deployment

Expansion opportunities:

- API access for downstream workflow automation
- Vertical packages for board governance, regulated teams, and customer operations

## 16. Go-To-Market Strategy

- Start with founder-led and leadership-heavy teams where meeting cost is highest.
- Win on a high-value wedge: decisions + action tracking from recurring meetings.
- Land via lightweight self-serve onboarding.
- Expand into organization-wide memory workflows and system integrations.
- Move upmarket with compliance, controls, and deployment flexibility.

## 17. Roadmap

### Phase 0 (Now): Prototype

- Local audio ingestion
- Live transcription stream
- Sentiment + decision extraction
- Meeting summary and PDF export

### Phase 1 (Hackathon): Product Proof

- Meeting-link initiated autonomous flow
- Structured decision/action schema
- Queryable meeting memory for recent sessions
- Better timeline and evidence mapping

### Phase 2: Beta

- Google Meet/Zoom/Teams integrations
- Action item ownership + status sync
- Semantic retrieval across meeting history
- Role-aware workspace access

### Phase 3: Scale

- Multi-tenant cloud architecture
- Enterprise governance and compliance controls
- Advanced analytics, trend detection, and proactive insights
- Deep integrations (Slack, Jira, Notion, CRM, ticketing)

## 18. How to Run the Prototype

### Prerequisites

- Python 3.10+ (3.11 recommended)
- Local microphone input configured
- Ollama installed and running
- Ollama models pulled: `llama3` and `mistral`

### Setup

```bash
=======
1. Project Title
MeetMind
Prototype codename in this repo: AI Board Meeting Analyzer

2. One-line Tagline
Turn meetings from fleeting conversations into durable, queryable organizational memory. 🧠

3. Vision
MeetMind is building an autonomous meeting intelligence system that joins meetings, listens in real time, converts speech into structured knowledge, and makes that knowledge searchable long after the call ends.

The product vision is not “better notes.”
It is a memory layer for teams: decisions, commitments, context, and rationale captured as institutional knowledge.

4. Deep Problem Statement
Meetings are where modern teams make decisions, surface risks, negotiate priorities, and commit to action. Yet the output of those meetings is mostly lost.

Operationally, the failure is obvious:

Decisions are made but not reliably documented.
Action items are implied, not assigned.
Teams re-discuss topics because prior context is hard to recover.
New team members cannot reconstruct why a decision was made.
Leadership lacks an auditable trail from discussion to execution.
Psychologically, the failure is worse:

People assume “someone else captured that.”
Participants multitask and miss nuance.
Late joiners interrupt flow and create recap tax.
Long recordings become graveyards of context nobody re-watches.
Human memory distorts details, ownership, and intent over time.
The result is predictable:

Missed tasks
Accountability gaps
Knowledge silos
Onboarding drag
Decision traceability failures
Slower execution despite more meetings
Teams generate knowledge every day. Most of it evaporates.

5. Why Existing Solutions Fail
Current tools usually solve only one layer:

Recording tools preserve raw media, not structured knowledge.
Transcript tools produce text dumps, not decision intelligence.
Note apps depend on manual discipline during high-cognitive-load conversations.
Summary bots provide snapshots, not a persistent, queryable memory graph.
Search is often keyword-only and weak on intent, ownership, and rationale.
The core gap: no system converts live conversation into durable, structured, and retrievable organizational memory.

6. Our Solution
MeetMind creates an end-to-end meeting intelligence pipeline:

Capture live meeting audio
Transcribe continuously
Extract decisions, action items, and key signals
Persist structured outputs
Generate concise summaries
Enable natural-language retrieval over historical meetings
This turns meetings into a searchable system of record, not a one-time event.

7. What Exists Today (Prototype Capabilities — Based on This Repo)
This repository currently implements a local prototype, not the full autonomous platform.

Implemented now:

FastAPI backend with Socket.IO streaming events
Start/stop meeting session endpoints
Local audio capture from default microphone (PyAudio)
Voice activity detection (webrtcvad)
Real-time chunk transcription via faster-whisper (tiny model)
LLM-based sentiment analysis and decision/action-item extraction via local Ollama (llama3 with mistral fallback)
Meeting/session persistence in SQLite (board_meetings.db) via SQLAlchemy
Summary generation endpoint per meeting
PDF export of meeting transcript and extracted decisions
Simple static frontend (index.html) for live transcript + meeting list + summary/export actions
Current prototype constraints:

No Google Meet auto-join yet
No conferencing platform integrations yet
No production auth, RBAC, or tenancy model
Speaker diarization is scaffolded but disabled in active flow (default speaker placeholder)
No vector search or cross-meeting semantic retrieval yet
No assignment/closure workflow for action items yet
Local-first architecture, not cloud deployment-ready
8. What We Are Building During This Hackathon
Hackathon scope is to prove the core wedge with a tighter end-to-end flow:

Meeting-link based autonomous session kickoff (initial Google Meet path)
Reliable real-time transcription + structured extraction in one pipeline
Explicit decision and action-item objects with ownership fields
Query-first meeting memory interface (“What did we decide about X?”)
Stronger meeting timeline view with citations to transcript segments
Consent and participation signaling built into session lifecycle
Hackathon goal: demonstrate a credible product loop from conversation to persistent, queryable intelligence.

9. Target Users
Primary user segments:

Startup founders and leadership teams running frequent decision-heavy meetings
Chiefs of Staff and program leads responsible for follow-through
Product and engineering managers coordinating cross-functional execution
RevOps, customer success, and account teams that need decision traceability
Compliance-sensitive teams that require auditable meeting records
10. Real Use Cases
Board and leadership meetings: capture strategic decisions and assigned owners instantly.
Product reviews: extract scope changes, blockers, and deadlines from discussion.
Customer escalation calls: retain commitments and rationale with searchable context.
Weekly operations standups: auto-track recurring blockers and unresolved items.
New hire onboarding: query prior meeting history to understand “why” behind current plans.
Cross-timezone collaboration: late joiners recover context without interrupting live flow.
11. How It Works (Technical Architecture Overview)
[Local Audio Input]
      |
      v
[PyAudio Capture] -> [WebRTC VAD]
      |
      v
[5s Audio Chunks]
      |
      v
[Faster-Whisper Transcription]
      |
      +--------------------------+
      |                          |
      v                          v
[Sentiment Analysis]      [Decision/Action Extraction]
        (Ollama)                 (Ollama)
      |                          |
      +------------+-------------+
                   v
        [SQLite Persistence]
                   |
        +----------+-----------+
        |                      |
        v                      v
 [Socket.IO Live Feed]   [Summary/PDF APIs]
        |                      |
        v                      v
 [Browser UI]          [Exported Reports]
12. Tech Stack
Layer	Current Prototype
API	FastAPI
Real-time transport	Socket.IO
Audio capture	PyAudio
Speech activity filter	webrtcvad
Transcription	faster-whisper
LLM analysis	Ollama (llama3, mistral fallback)
Persistence	SQLite + SQLAlchemy
Reporting	ReportLab (PDF export)
Frontend	Static HTML/CSS/JS
13. Differentiation / Competitive Advantage
Memory-first architecture: designed around persistent knowledge, not just transcription.
Structured intelligence output: decisions and actions as data objects, not only prose summaries.
Real-time + retrospective value: useful during the meeting and after.
Local-first prototype path: fast iteration loop with privacy-friendly defaults.
Clear enterprise expansion path: platform integrations, policy controls, auditability, multi-tenant architecture.
14. Privacy & Consent Model
Design principles:

Explicit participant notice before capture
Consent-aware join behavior
Role-based access to transcripts and summaries
Configurable retention and deletion policies
Encryption and auditable access trails in production architecture
Prototype reality in this repo:

Runs locally
Stores meeting artifacts in local SQLite and local PDF exports
Does not yet implement full consent workflow, identity, or policy enforcement
15. Monetization Strategy
Planned model:

Per-host subscription for core meeting intelligence
Usage-based processing for transcription/analysis minutes
Team plan with shared memory/search and integrations
Enterprise tier for compliance controls, SSO, governance, custom retention, and private deployment
Expansion opportunities:

API access for downstream workflow automation
Vertical packages for board governance, regulated teams, and customer operations
16. Go-To-Market Strategy
Start with founder-led and leadership-heavy teams where meeting cost is highest.
Win on a high-value wedge: decisions + action tracking from recurring meetings.
Land via lightweight self-serve onboarding.
Expand into organization-wide memory workflows and system integrations.
Move upmarket with compliance, controls, and deployment flexibility.
17. Roadmap
Phase 0 (Now): Prototype

Local audio ingestion
Live transcription stream
Sentiment + decision extraction
Meeting summary and PDF export
Phase 1 (Hackathon): Product Proof

Meeting-link initiated autonomous flow
Structured decision/action schema
Queryable meeting memory for recent sessions
Better timeline and evidence mapping
Phase 2: Beta

Google Meet/Zoom/Teams integrations
Action item ownership + status sync
Semantic retrieval across meeting history
Role-aware workspace access
Phase 3: Scale

Multi-tenant cloud architecture
Enterprise governance and compliance controls
Advanced analytics, trend detection, and proactive insights
Deep integrations (Slack, Jira, Notion, CRM, ticketing)
18. How to Run the Prototype
Prerequisites
Python 3.10+ (3.11 recommended)
Local microphone input configured
Ollama installed and running
Ollama models pulled: llama3 and mistral
Setup
>>>>>>> 6981941b4729cc6026eadc6fc6aa88445b2746eb
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
ollama pull llama3
ollama pull mistral
<<<<<<< HEAD
```

### Start backend (from repo root)

```bash
python -m uvicorn backend.app.main:socket_app --host 0.0.0.0 --port 8003
```

### Start frontend (new terminal)

```bash
cd frontend
python -m http.server 5500
```

Open:

- `http://127.0.0.1:5500`

Use the UI:

- Start Meeting to begin local capture
- Stop Meeting to end session
- Summary for generated recap
- Export PDF to download report

Artifacts:

- Database: `board_meetings.db`
- Exports: `exports/`

Optional scripts:

```bash
python run_test_meeting.py
python test_api.py
```

## 19. Long-Term Vision

=======
Start backend (from repo root)
python -m uvicorn backend.app.main:socket_app --host 0.0.0.0 --port 8003
Start frontend (new terminal)
cd frontend
python -m http.server 5500
Open:

http://127.0.0.1:5500
Use the UI:

Start Meeting to begin local capture
Stop Meeting to end session
Summary for generated recap
Export PDF to download report
Artifacts:

Database: board_meetings.db
Exports: exports/
Optional scripts:

python run_test_meeting.py
python test_api.py
19. Long-Term Vision
>>>>>>> 6981941b4729cc6026eadc6fc6aa88445b2746eb
MeetMind becomes the intelligence substrate for organizational conversations.

Every meeting should create durable, trustworthy memory:

<<<<<<< HEAD
- What was decided
- Why it was decided
- Who owns follow-through
- What changed over time

When meetings become queryable knowledge instead of forgotten conversations, teams execute faster, onboard better, and make higher-quality decisions with less friction.
=======
What was decided
Why it was decided
Who owns follow-through
What changed over time
When meetings become queryable knowledge instead of forgotten conversations, teams execute faster, onboard better, and make higher-quality decisions with less friction.
>>>>>>> 6981941b4729cc6026eadc6fc6aa88445b2746eb