/**
 * ChatPage — main chat interface.
 *
 * Responsibilities:
 * - Thread management: persist thread_id in sessionStorage per API contract.
 * - Health check: show connection status in header.
 * - Chat request/response: call POST /api/chat with correct thread_id.
 * - Render message list with citations and booking panels.
 * - New Chat action: clears local state and sessionStorage thread_id.
 *
 * The backend is always authoritative; the UI never reconstructs or modifies
 * server-side conversation state.
 */

import {
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'react';
import { sendChatMessage, fetchHealth, ApiClientError } from '../api/client';
import type { HealthResponse, AgentInfo } from '../api/types';
import { MessageBubble, type Message } from './MessageBubble';
import { MessageComposer } from './MessageComposer';
import { EmptyState } from './EmptyState';
import './ChatPage.css';

const THREAD_STORAGE_KEY = 'aha_thread_id';

let _msgCounter = 0;
function nextId() {
  return `msg-${++_msgCounter}-${Date.now()}`;
}

type ConnectionState = 'loading' | 'connected' | 'degraded' | 'disconnected';

export function ChatPage() {
  // --- Connection status ---
  const [connState, setConnState] = useState<ConnectionState>('loading');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  // --- Thread ---
  const [threadId, setThreadId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(THREAD_STORAGE_KEY);
    } catch {
      return null;
    }
  });

  // --- Messages ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [agentInfo, setAgentInfo] = useState<AgentInfo | null>(null);

  // --- Scroll ---
  const listEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // --- Health check on mount ---
  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await fetchHealth();
        if (cancelled) return;
        setHealthData(data);
        if (data.status === 'ok') setConnState('connected');
        else if (data.status === 'degraded') setConnState('degraded');
        else setConnState('disconnected');
      } catch {
        if (!cancelled) setConnState('disconnected');
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  // --- Auto-scroll to bottom ---
  useEffect(() => {
    if (isAtBottom) {
      listEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, isAtBottom]);

  // --- Track scroll position to suppress auto-scroll when user reads history ---
  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setIsAtBottom(atBottom);
  }

  // --- Save thread_id to sessionStorage whenever it changes ---
  useEffect(() => {
    try {
      if (threadId) sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
      else sessionStorage.removeItem(THREAD_STORAGE_KEY);
    } catch {
      // sessionStorage not available (unlikely in a modern browser)
    }
  }, [threadId]);

  // --- Send message ---
  const handleSend = useCallback(async (overrideMessage?: string) => {
    const text = (overrideMessage ?? inputValue).trim();
    if (!text || isSending) return;

    setInputValue('');
    setIsSending(true);

    // Optimistically add user message
    const userMsg: Message = {
      id: nextId(),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };

    // Thinking indicator
    const thinkingId = nextId();
    const thinkingMsg: Message = {
      id: thinkingId,
      role: 'assistant',
      content: '',
      isThinking: true,
    };

    setMessages(prev => [...prev, userMsg, thinkingMsg]);
    setIsAtBottom(true);

    try {
      const response = await sendChatMessage({
        thread_id: threadId ?? null,
        message: text,
      });

      // Update thread_id from server response
      if (response.thread_id) {
        setThreadId(response.thread_id);
      }

      setAgentInfo(response.agent);

      const assistantMsg: Message = {
        id: response.reply.message_id,
        role: 'assistant',
        content: response.reply.content,
        citations: response.reply.citations,
        booking: response.booking,
        createdAt: response.reply.created_at,
      };

      // Replace thinking with real response
      setMessages(prev => prev.filter(m => m.id !== thinkingId).concat(assistantMsg));
    } catch (err) {
      const errText = err instanceof ApiClientError
        ? err.message
        : err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.';

      const isRetryable = err instanceof ApiClientError
        ? (err.details as { error?: { retryable?: boolean } } | null)?.error?.retryable !== false
        : true;

      const errorMsg: Message = {
        id: nextId(),
        role: 'error',
        content: errText + (isRetryable ? '\n\nYour message has been preserved — you can try again.' : ''),
        isError: true,
      };

      // Remove thinking, keep user message, add error
      setMessages(prev => prev.filter(m => m.id !== thinkingId).concat(errorMsg));

      // Restore input on recoverable errors
      setInputValue(text);
    } finally {
      setIsSending(false);
    }
  }, [inputValue, isSending, threadId]);

  // --- New Chat ---
  function handleNewChat() {
    setThreadId(null);
    setMessages([]);
    setAgentInfo(null);
    setInputValue('');
    setIsAtBottom(true);
  }

  return (
    <div className="chat-page">
      {/* Header */}
      <header className="chat-header" role="banner">
        <div className="chat-header-left">
          <span className="chat-logo" aria-hidden="true">📖</span>
          <div className="chat-identity">
            <h1 className="chat-title">Agentic Handbook Assistant</h1>
            {agentInfo && (
              <div className="agent-route" aria-label="Agent route">
                {agentInfo.route.map((node, i) => (
                  <span key={i} className="route-node">{node}</span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="chat-header-right">
          {/* Connection status */}
          <ConnectionPill state={connState} healthData={healthData} />

          {/* Thread indicator */}
          {threadId && (
            <div className="thread-indicator" title={`Thread: ${threadId}`}>
              <span className="thread-label">Session</span>
              <span className="thread-id">{threadId.slice(0, 8)}…</span>
            </div>
          )}

          {/* New Chat button */}
          <button
            id="new-chat-btn"
            type="button"
            className="new-chat-btn"
            onClick={handleNewChat}
            aria-label="Start a new conversation"
            title="New Chat"
          >
            <span aria-hidden="true">＋</span>
            <span className="new-chat-label">New Chat</span>
          </button>
        </div>
      </header>

      {/* Message list */}
      <main
        className="chat-main"
        ref={listRef}
        onScroll={handleScroll}
        aria-label="Conversation"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length === 0 ? (
          <EmptyState onSelectPrompt={text => handleSend(text)} />
        ) : (
          <div className="message-list" role="list">
            {messages.map(msg => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={listEndRef} aria-hidden="true" />
          </div>
        )}

        {/* Scroll to bottom button */}
        {!isAtBottom && messages.length > 0 && (
          <button
            type="button"
            className="scroll-to-bottom"
            onClick={() => {
              setIsAtBottom(true);
              listEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            aria-label="Scroll to latest message"
          >
            ↓
          </button>
        )}
      </main>

      {/* Composer */}
      <MessageComposer
        value={inputValue}
        onChange={setInputValue}
        onSubmit={() => handleSend()}
        isSending={isSending}
        disabled={connState === 'disconnected'}
      />
    </div>
  );
}

/* Connection status pill */
function ConnectionPill({
  state,
  healthData,
}: {
  state: ConnectionState;
  healthData: HealthResponse | null;
}) {
  const labels: Record<ConnectionState, string> = {
    loading: 'Connecting…',
    connected: 'Connected',
    degraded: 'Degraded',
    disconnected: 'Offline',
  };

  const llmOk = healthData?.components.llm.status === 'configured';
  const ragOk = (healthData?.components.vector_store.chunk_count ?? 0) > 0;

  let tooltip = labels[state];
  if (state === 'connected' && healthData) {
    const issues: string[] = [];
    if (!llmOk) issues.push('LLM not configured');
    if (!ragOk) issues.push('RAG index empty');
    if (issues.length) tooltip = `Connected (${issues.join(', ')})`;
  }

  return (
    <div
      className={`connection-pill pill-${state}`}
      title={tooltip}
      aria-label={`Backend status: ${tooltip}`}
      role="status"
    >
      <span className={`pill-dot dot-${state}`} aria-hidden="true" />
      <span className="pill-label">{labels[state]}</span>
    </div>
  );
}
