import { useState, useEffect, useCallback } from 'react';
import { fetchHealth, ApiClientError } from './api/client';
import type { HealthResponse } from './api/types';
import './App.css';

type ConnectionState = 'loading' | 'connected' | 'disconnected';

export default function App() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const checkConnection = useCallback(async () => {
    setErrorMessage(null);
    setConnectionState('loading');

    try {
      const data = await fetchHealth();
      setHealthData(data);
      setConnectionState('connected');
      setLastChecked(new Date());
    } catch (err) {
      setConnectionState('disconnected');
      setHealthData(null);
      setLastChecked(new Date());
      if (err instanceof ApiClientError || err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred while communicating with the backend.');
      }
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    async function initialCheck() {
      try {
        const data = await fetchHealth();
        if (!ignore) {
          setHealthData(data);
          setConnectionState('connected');
          setLastChecked(new Date());
        }
      } catch (err) {
        if (!ignore) {
          setConnectionState('disconnected');
          setHealthData(null);
          setLastChecked(new Date());
          if (err instanceof ApiClientError || err instanceof Error) {
            setErrorMessage(err.message);
          } else {
            setErrorMessage('An unexpected error occurred while communicating with the backend.');
          }
        }
      }
    }

    initialCheck();

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="badge-container">
          <span className="phase-badge">Phase 1 Foundation</span>
          <span className="tech-badge">FastAPI + React TS</span>
        </div>
        <h1 className="app-title">Agentic Handbook Assistant</h1>
        <p className="app-subtitle">
          Full-stack agentic AI application orchestrating employee handbook policy Q&A with grounded
          citations and deterministic multi-turn meeting scheduling.
        </p>
      </header>

      <main className="main-content">
        <section className="card status-card">
          <div className="card-header">
            <div>
              <h2 className="card-title">Backend Connectivity</h2>
              <p className="card-description">
                Verifying the HTTP communication path: Browser &rarr; Vite Dev Proxy (`/api`) &rarr; FastAPI (`localhost:8000`)
              </p>
            </div>
            <div className={`status-pill status-${connectionState}`}>
              <span className="status-dot"></span>
              <span className="status-label">
                {connectionState === 'loading' && 'Checking Backend...'}
                {connectionState === 'connected' && 'Connected'}
                {connectionState === 'disconnected' && 'Disconnected'}
              </span>
            </div>
          </div>

          <div className="card-body">
            {connectionState === 'loading' && (
              <div className="state-panel loading-panel" role="status">
                <div className="spinner" aria-hidden="true"></div>
                <div>
                  <p className="panel-primary-text">Querying <code>GET /api/health</code></p>
                  <p className="panel-secondary-text">Checking server responsiveness and configuration diagnostics...</p>
                </div>
              </div>
            )}

            {connectionState === 'connected' && healthData && (
              <div className="state-panel connected-panel">
                <div className="metrics-grid">
                  <div className="metric-box">
                    <span className="metric-label">Service Status</span>
                    <span className="metric-value metric-success">{healthData.status.toUpperCase()}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">API Version</span>
                    <span className="metric-value">{healthData.version}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">Server Timestamp</span>
                    <span className="metric-value metric-time" title={healthData.time}>
                      {new Date(healthData.time).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">Transport Path</span>
                    <span className="metric-value">Vite Proxy &rarr; :8000</span>
                  </div>
                </div>

                <div className="subsystems-section">
                  <h3 className="section-title">Subsystem Diagnostic Status (from API Contract §4)</h3>
                  <div className="subsystems-grid">
                    <div className="subsystem-item">
                      <div className="subsystem-header">
                        <span className="subsystem-name">Vector Store (ChromaDB)</span>
                        <span className="subsystem-tag tag-neutral">{healthData.components.vector_store.status}</span>
                      </div>
                      <p className="subsystem-desc">
                        Collection: <code>{healthData.components.vector_store.collection}</code> | Chunks: {healthData.components.vector_store.chunk_count} (Ingestion scheduled for Phase 4)
                      </p>
                    </div>

                    <div className="subsystem-item">
                      <div className="subsystem-header">
                        <span className="subsystem-name">Checkpointer (SQLite)</span>
                        <span className="subsystem-tag tag-neutral">{healthData.components.checkpointer.status}</span>
                      </div>
                      <p className="subsystem-desc">
                        Backend: <code>{healthData.components.checkpointer.backend}</code> (LangGraph persistence scheduled for Phase 3/6)
                      </p>
                    </div>

                    <div className="subsystem-item">
                      <div className="subsystem-header">
                        <span className="subsystem-name">LLM Gateway</span>
                        <span className={`subsystem-tag ${healthData.components.llm.status === 'configured' ? 'tag-success' : 'tag-neutral'}`}>
                          {healthData.components.llm.status}
                        </span>
                      </div>
                      <p className="subsystem-desc">
                        Provider: <code>{healthData.components.llm.provider}</code> (Turn analysis & grounded answers scheduled for Phase 4)
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {connectionState === 'disconnected' && (
              <div className="state-panel disconnected-panel" role="alert">
                <div className="error-icon" aria-hidden="true">&times;</div>
                <div className="error-content">
                  <h3 className="error-title">Unable to reach FastAPI backend</h3>
                  <p className="error-message">{errorMessage}</p>
                  <div className="troubleshooting-guide">
                    <strong>Troubleshooting Checklist:</strong>
                    <ul>
                      <li>Ensure FastAPI is running: <code>uvicorn app.main:app --port 8000</code> in the <code>backend/</code> folder.</li>
                      <li>Verify Vite's dev server is running on port 5173 with the proxy configured in <code>vite.config.ts</code>.</li>
                      <li>Check that port 8000 is not blocked by another Windows process or firewall.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="card-footer">
            <button
              id="retry-health-btn"
              type="button"
              className="btn btn-primary"
              onClick={checkConnection}
              disabled={connectionState === 'loading'}
            >
              {connectionState === 'loading' ? 'Checking...' : 'Retry Health Check'}
            </button>
            {lastChecked && (
              <span className="last-checked-text">
                Last checked: {lastChecked.toLocaleTimeString()}
              </span>
            )}
          </div>
        </section>

        <section className="card roadmap-card">
          <h2 className="card-title">Architecture & Phase Roadmap</h2>
          <div className="roadmap-grid">
            <div className="roadmap-step step-complete">
              <span className="step-num">1</span>
              <h4>Foundation (Active)</h4>
              <p>Repo layout, config hygiene, FastAPI health endpoint, Vite dev proxy, automated tests.</p>
            </div>
            <div className="roadmap-step">
              <span className="step-num">2</span>
              <h4>API Shell & Chat Stub</h4>
              <p>Thread ID validation, error envelope, request tracing, ChatService stub.</p>
            </div>
            <div className="roadmap-step">
              <span className="step-num">3</span>
              <h4>LangGraph Skeleton</h4>
              <p>State schema, merge reducer, 9 graph nodes, MemorySaver persistence smoke test.</p>
            </div>
            <div className="roadmap-step">
              <span className="step-num">4</span>
              <h4>PDF Ingestion & RAG</h4>
              <p>PyPDF parsing, ChromaDB embeddings, grounded answers with code citations.</p>
            </div>
            <div className="roadmap-step">
              <span className="step-num">5</span>
              <h4>Booking Tools</h4>
              <p>Deterministic slot inventory, validation, multi-turn booking state machine.</p>
            </div>
            <div className="roadmap-step">
              <span className="step-num">6</span>
              <h4>Context Interleaving</h4>
              <p>SQLite checkpointing, FAQ mid-booking handling without parameter loss.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>Agentic Handbook Assistant &bull; Internship Assessment Technical Project</p>
      </footer>
    </div>
  );
}
