# Board Meeting Analyzer

AI-powered tool to capture meetings, analyze discussions, and query transcript content.

## Quick Start

1. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Frontend
```bash
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000` and calls backend routes under `/api`.

## Frontend to Backend Connection

- Default (recommended): use CRA proxy in `frontend/package.json` and keep:
  - `REACT_APP_API_URL=/api`
- Optional direct backend URL:
  - `REACT_APP_API_URL=http://localhost:8000/api`

The frontend API client is centralized in `frontend/src/services/api.js`.
