/**
 * MessageComposer — multiline textarea + send button.
 * - Enter sends, Shift+Enter adds newline.
 * - Disabled while a request is in flight.
 * - Preserves user input on recoverable errors.
 */

import { useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react';
import './MessageComposer.css';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isSending: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageComposer({
  value,
  onChange,
  onSubmit,
  isSending,
  disabled = false,
  placeholder = 'Ask a handbook question or start a booking…',
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea as content grows
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  const canSubmit = value.trim().length > 0 && !isSending && !disabled;

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSubmit) onSubmit();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <form
      className="composer-form"
      onSubmit={handleSubmit}
      aria-label="Message composer"
      noValidate
    >
      <div className={`composer-inner ${isSending ? 'composer-sending' : ''} ${disabled ? 'composer-disabled' : ''}`}>
        <textarea
          id="chat-input"
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Your message"
          disabled={isSending || disabled}
          rows={1}
          maxLength={2000}
          autoComplete="off"
          spellCheck={true}
        />

        <button
          id="send-btn"
          type="submit"
          className={`composer-send-btn ${canSubmit ? 'send-ready' : ''}`}
          disabled={!canSubmit}
          aria-label={isSending ? 'Sending…' : 'Send message'}
          title={isSending ? 'Sending…' : 'Send (Enter)'}
        >
          {isSending ? (
            <span className="send-spinner" aria-hidden="true" />
          ) : (
            <SendIcon />
          )}
        </button>
      </div>

      <div className="composer-hints">
        <span className="composer-hint">Enter to send · Shift+Enter for new line</span>
        {value.length > 1800 && (
          <span className="composer-char-count" aria-live="polite">
            {value.length}/2000
          </span>
        )}
      </div>
    </form>
  );
}

function SendIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M14.5 8L1.5 2L4 8L1.5 14L14.5 8Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="0.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
