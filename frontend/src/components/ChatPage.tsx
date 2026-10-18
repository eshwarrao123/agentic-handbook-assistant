/**
 * ChatPage — Editorial workspace with sidebar navigation
 */

import {
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'react';
import { BookOpen, Plus, ArrowDown } from 'lucide-react';
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
  const [_healthData, _setHealthData] = useState<HealthResponse | null>(null);

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
  const [_agentInfo, _setAgentInfo] = useState<AgentInfo | null>(null);

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
        _setHealthData(data);
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

  // --- Track scroll position ---
  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setIsAtBottom(atBottom);
  }

  // --- Save thread_id to sessionStorage ---
  useEffect(() => {
    try {
      if (threadId) sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
      else sessionStorage.removeItem(THREAD_STORAGE_KEY);
    } catch {
      // sessionStorage not available
    }
  }, [threadId]);

  // --- Send message ---
  const handleSend = useCallback(async (overrideMessage?: string) => {
    const text = (overrideMessage ?? inputValue).trim();
    if (!text || isSending) return;

    setInputValue('');
    setIsSending(true);

    const userMsg: Message = {
      id: nextId(),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };

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

      if (response.thread_id) {
        setThreadId(response.thread_id);
      }

      _setAgentInfo(response.agent);

      const assistantMsg: Message = {
        id: response.reply.message_id,
        role: 'assistant',
        content: response.reply.content,
        createdAt: response.reply.created_at,
        citations: response.reply.citations,
        booking: response.booking,
      };

      setMessages(prev => prev.filter(m => m.id !== thinkingId).concat(assistantMsg));
    } catch (err) {
      const errorMsg: Message = {
        id: nextId(),
        role: 'error',
        content: err instanceof ApiClientError 
          ? `Error: ${err.message}` 
          : 'An unexpected error occurred. Please try again.',
        createdAt: new Date().toISOString(),
      };

      setMessages(prev => prev.filter(m => m.id !== thinkingId).concat(errorMsg));
    } finally {
      setIsSending(false);
    }
  }, [inputValue, isSending, threadId]);

  // --- New Chat ---
  const handleNewChat = useCallback(() => {
    setMessages([]);
    setThreadId(null);
    setInputValue('');
    _setAgentInfo(null);
  }, []);

  // --- Prompt selection ---
  const handleSelectPrompt = useCallback((prompt: string) => {
    setInputValue(prompt);
    setTimeout(() => handleSend(prompt), 100);
  }, [handleSend]);



  return (
    <div className="chat-page">
      {/* Workspace Rail (Sidebar) */}
      <aside className="workspace-rail" role="complementary">
        <div className="rail-header">
          <div className="rail-logo">
            <BookOpen className="rail-icon" aria-hidden="true" />
            <div>
              <div className="rail-title">Handbook Assistant</div>
            </div>
          </div>
          <p className="rail-subtitle">
            Search policies and schedule appointments
          </p>
        </div>

        <nav className="rail-nav" aria-label="Main navigation">
          <button
            type="button"
            className="rail-nav-item"
            onClick={handleNewChat}
            aria-label="Start new conversation"
          >
            <Plus className="rail-nav-icon" aria-hidden="true" />
            New Chat
          </button>
        </nav>

        <div className="rail-divider" />

        <div className="rail-footer">
          <div className="rail-status" role="status">
            <span className={`status-dot status-${connState}`} aria-hidden="true" />
            <span>
              {connState === 'loading' && 'Connecting...'}
              {connState === 'connected' && 'Connected'}
              {connState === 'degraded' && 'Degraded'}
              {connState === 'disconnected' && 'Disconnected'}
            </span>
          </div>

          {threadId && (
            <div className="rail-thread" title={`Thread ID: ${threadId}`}>
              {threadId.slice(0, 8)}...
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <div className="chat-content">
        <header className="chat-header">
          <h1 className="header-title">
            {messages.length === 0 ? 'New Conversation' : 'Conversation'}
          </h1>
          <button
            type="button"
            className="new-chat-btn"
            onClick={handleNewChat}
            aria-label="Start new chat"
          >
            <Plus className="btn-icon" aria-hidden="true" />
            <span>New Chat</span>
          </button>
        </header>

        <main
          className="chat-main"
          ref={listRef}
          onScroll={handleScroll}
          role="main"
        >
          {messages.length === 0 ? (
            <EmptyState onSelectPrompt={handleSelectPrompt} />
          ) : (
            <div className="message-list">
              {messages.map(msg => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={listEndRef} />
            </div>
          )}

          {!isAtBottom && messages.length > 0 && (
            <button
              type="button"
              className="scroll-to-bottom"
              onClick={() => setIsAtBottom(true)}
              aria-label="Scroll to bottom"
            >
              <ArrowDown className="scroll-icon" aria-hidden="true" />
            </button>
          )}
        </main>

        <MessageComposer
          value={inputValue}
          onChange={setInputValue}
          onSend={() => handleSend()}
          disabled={connState === 'disconnected'}
          isSending={isSending}
        />
      </div>
    </div>
  );
}
