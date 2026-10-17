# Agentic Handbook Assistant

Full-stack agentic AI assistant built for a technical internship assessment. The application combines interactive employee handbook exploration, grounded policy Q&A with verifiable page-level citations, and deterministic multi-turn meeting slot booking with context interleaving.

---

## 1. Architecture Overview

- **Frontend:** React 19, TypeScript, and Vite. Configured with a development proxy routing `/api/*` to FastAPI on port 8000.
- **Backend:** Python 3.10+, FastAPI, and Uvicorn. Implements clean HTTP routing, Pydantic schemas, and request tracing via `X-Request-ID`.
- **Orchestration (Upcoming Phase 3+):** A single compiled LangGraph `StateGraph` managing turn analysis, deterministic booking tools, grounded FAQ retrieval, and context resumption.
- **RAG & Storage (Upcoming Phase 4+):** Page-bounded chunking with local embeddings, ChromaDB vector store, and SQLite checkpointer for multi-turn persistence.

---

## 2. Project Status & Roadmap

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | **Repository Foundation & Connectivity** (FastAPI health endpoint, Vite proxy, automated tests, documentation alignment) | **Completed & Verified** |
| Phase 2 | API Shell & Chat Endpoint Stub | Planned |
| Phase 3 | LangGraph State Schema & Graph Skeleton | Planned |
| Phase 4 | PDF Ingestion & Calibrated Grounded RAG | Planned |
| Phase 5 | Deterministic Booking Service & Multi-turn Tooling | Planned |
| Phase 6 | Checkpoint Persistence & Context Interleaving | Planned |
| Phase 7 | Chat UI, Citation Display & Booking Cards | Planned |
| Phase 8 | End-to-End Verification, Evidence Artifacts & Submission | Planned |

---

## 3. Repository Layout

```
agentic-handbook-assistant/
├── README.md                  # Project overview and execution guide
├── .gitignore                 # Excludes venvs, secrets, data, node_modules, and artifacts
├── docs/                      # Planning reference documents and learning notes
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── TECHNICAL_DESIGN.md
│   ├── API_CONTRACT.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TEST_PLAN.md
│   ├── ASSESSMENT_TRACEABILITY.md
│   ├── LEARNING_ROADMAP.md
│   ├── LEARNING_NOTES.md
│   └── AI_ENGINEERING_LOG.md
├── backend/
│   ├── requirements.txt       # Pinned runtime dependencies (FastAPI, Uvicorn, etc.)
│   ├── requirements-dev.txt   # Development dependencies (pytest, httpx)
│   ├── pytest.ini             # Pytest configuration
│   ├── .env.example           # Harmless environment placeholders
│   ├── app/
│   │   ├── main.py            # FastAPI factory, CORS, request tracing middleware
│   │   ├── config.py          # Pydantic Settings
│   │   └── api/
│   │       ├── schemas.py     # Request/response schemas (API_CONTRACT §4)
│   │       └── routes_health.py # GET /api/health endpoint
│   └── tests/
│       ├── conftest.py        # TestClient fixture
│       └── api/
│           └── test_health.py # Automated health endpoint tests
└── frontend/
    ├── package.json           # React, Vite, TypeScript dependencies
    ├── vite.config.ts         # Port 5173 and /api proxy configuration
    ├── .env.example           # Optional VITE_API_BASE_URL placeholder
    └── src/
        ├── App.tsx            # Development connectivity dashboard
        ├── App.css            # Scoped dashboard styling
        ├── index.css          # Core CSS variables and tokens
        └── api/
            ├── types.ts       # TypeScript contract types
            └── client.ts      # Fetch client using relative /api path
```

---

## 4. Local Execution Guide (Windows PowerShell)

Follow these instructions to run and verify the project on Windows 11 using PowerShell.

### 4.1 Backend Setup and Execution

Open **Terminal 1** in the repository root:

```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a Python virtual environment (if not already created)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install backend dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Run automated backend tests
python -m pytest -v

# 5. Start the FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be available at:
- Health endpoint: `http://localhost:8000/api/health`
- Interactive OpenAPI documentation: `http://localhost:8000/docs`

### 4.2 Frontend Setup and Execution

Open **Terminal 2** in the repository root:

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Run production build and TypeScript type-check
npm run build

# 4. Run the linter
npm run lint

# 5. Start the Vite development server
npm run dev
```

The frontend will be available at:
- Web Application: `http://localhost:5173`

---

## 5. Architectural Communication & Troubleshooting

### Why Two Separate Terminals?
- **Backend (Port 8000):** Runs the Python Uvicorn server executing asynchronous HTTP route handlers.
- **Frontend (Port 5173):** Runs the Vite Node.js development server providing Hot Module Replacement (HMR) and serving client-side assets.

### Request Flow
```
Browser (localhost:5173) ──> fetch('/api/health') ──> Vite Dev Proxy ──> FastAPI (localhost:8000/api/health)
```

### Isolating Issues:
1. **Server-side failure:** If `http://localhost:8000/api/health` returns an error or connection refused in a browser tab, the problem is in FastAPI, port availability, or Python dependencies.
2. **Proxy failure:** If direct access to port 8000 works, but `http://localhost:5173/api/health` returns a 504 Gateway Timeout or 404, check `frontend/vite.config.ts` proxy configuration.
3. **Frontend failure:** If the API response arrives (visible in the browser DevTools Network tab with status 200), but the UI shows an error or blank screen, the issue is in React state rendering or type parsing.
