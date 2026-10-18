/**
 * MessageBubble — renders a single conversation message.
 * Handles user messages, assistant messages (with citations and booking),
 * thinking indicator, and error messages.
 */

import type { Citation, BookingSnapshot } from '../api/types';
import { CitationList } from './CitationCard';
import { BookingPanel } from './BookingPanel';
import './MessageBubble.css';

export type MessageRole = 'user' | 'assistant' | 'error';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  booking?: BookingSnapshot;
  /** ISO timestamp */
  createdAt?: string;
  /** Set when this is a transient error message */
  isError?: boolean;
  /** Set to true while assistant is replying */
  isThinking?: boolean;
}

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  if (message.isThinking) {
    return (
      <div className="message-row message-row-assistant" role="status" aria-label="Assistant is thinking">
        <div className="message-avatar assistant-avatar" aria-hidden="true">A</div>
        <div className="message-body">
          <div className="thinking-indicator" aria-hidden="true">
            <span className="thinking-dot" style={{ animationDelay: '0ms' }} />
            <span className="thinking-dot" style={{ animationDelay: '160ms' }} />
            <span className="thinking-dot" style={{ animationDelay: '320ms' }} />
          </div>
        </div>
      </div>
    );
  }

  const isUser = message.role === 'user';
  const isError = message.role === 'error' || message.isError;

  return (
    <div
      className={`message-row message-row-${isUser ? 'user' : isError ? 'error' : 'assistant'}`}
      role="listitem"
    >
      {!isUser && (
        <div
          className={`message-avatar ${isError ? 'error-avatar' : 'assistant-avatar'}`}
          aria-hidden="true"
        >
          {isError ? '!' : 'A'}
        </div>
      )}

      <div className="message-body">
        <div className={`message-bubble ${isUser ? 'bubble-user' : isError ? 'bubble-error' : 'bubble-assistant'}`}>
          <MessageContent content={message.content} />
        </div>

        {/* Citations only on assistant messages */}
        {!isUser && !isError && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {/* Booking panel */}
        {!isUser && !isError && message.booking && message.booking.status !== 'none' && (
          <BookingPanel booking={message.booking} />
        )}

        {/* Timestamp */}
        {message.createdAt && (
          <time
            className={`message-time ${isUser ? 'time-user' : 'time-assistant'}`}
            dateTime={message.createdAt}
            title={message.createdAt}
          >
            {formatTime(message.createdAt)}
          </time>
        )}
      </div>

      {isUser && (
        <div className="message-avatar user-avatar" aria-hidden="true">
          U
        </div>
      )}
    </div>
  );
}

/** Render message content preserving newlines */
function MessageContent({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>
          {line}
          {i < lines.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}
