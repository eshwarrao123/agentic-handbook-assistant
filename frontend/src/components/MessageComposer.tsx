/**
 * MessageComposer — Message input with send button
 */

import { useRef, useEffect, type KeyboardEvent, type FormEvent } from 'react';
import { Send } from 'lucide-react';
import './MessageComposer.css';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  isSending: boolean;
}

export function MessageComposer({ value, onChange, onSend, disabled, isSending }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled && !isSending) {
        onSend();
      }
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim() && !disabled && !isSending) {
      onSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled && !isSending;

  return (
    <div className="message-composer">
      <form onSubmit={handleSubmit} className="composer-container">
        <div className="composer-input-wrapper">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the handbook or request an appointment..."
            disabled={disabled}
            aria-label="Message input"
            rows={1}
          />
          <div className="composer-hint">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
        <button
          type="submit"
          className={`composer-send-btn ${canSend ? 'send-ready' : ''}`}
          disabled={!canSend}
          aria-label="Send message"
        >
          {isSending ? (
            <span className="send-spinner" aria-hidden="true" />
          ) : (
            <Send className="send-icon" aria-hidden="true" />
          )}
        </button>
      </form>
    </div>
  );
}
