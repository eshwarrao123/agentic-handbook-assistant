/**
 * MessageBubble — renders user and assistant messages with citations and booking panels
 */

import { User, Bot, AlertCircle } from 'lucide-react';
import type { Citation, BookingSnapshot } from '../api/types';
import { CitationList } from './CitationCard';
import { BookingPanel } from './BookingPanel';
import './MessageBubble.css';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  createdAt?: string;
  isThinking?: boolean;
  citations?: Citation[];
  booking?: BookingSnapshot;
}

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const { role, content, isThinking, citations, booking, createdAt } = message;

  if (isThinking) {
    return (
      <div className="message-row message-row-assistant">
        <div className="message-avatar assistant-avatar">
          <Bot className="avatar-icon" aria-hidden="true" />
        </div>
        <div className="message-body">
          <div className="thinking-indicator" aria-label="Thinking">
            <div className="thinking-dot" />
            <div className="thinking-dot" />
            <div className="thinking-dot" />
          </div>
        </div>
      </div>
    );
  }

  const rowClass = `message-row message-row-${role}`;
  const bubbleClass = `message-bubble bubble-${role}`;

  return (
    <div className={rowClass}>
      <div className={`message-avatar ${role}-avatar`}>
        {role === 'user' && <User className="avatar-icon" aria-hidden="true" />}
        {role === 'assistant' && <Bot className="avatar-icon" aria-hidden="true" />}
        {role === 'error' && <AlertCircle className="avatar-icon" aria-hidden="true" />}
      </div>
      <div className="message-body">
        <div className={bubbleClass}>
          {content}
        </div>
        {citations && citations.length > 0 && (
          <CitationList citations={citations} />
        )}
        {booking && booking.status !== 'none' && (
          <BookingPanel booking={booking} />
        )}
        {createdAt && (
          <time className="message-time" dateTime={createdAt}>
            {new Date(createdAt).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </time>
        )}
      </div>
    </div>
  );
}
