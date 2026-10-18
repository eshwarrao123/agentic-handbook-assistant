/**
 * EmptyState — shown when the conversation has no messages.
 * Provides product identity and example prompts.
 */

import './EmptyState.css';

interface Props {
  onSelectPrompt: (prompt: string) => void;
}

const EXAMPLE_PROMPTS = [
  { emoji: '📋', text: 'How often are performance reviews conducted?' },
  { emoji: '🔒', text: 'What does the handbook say about data security?' },
  { emoji: '📅', text: 'I need to book a Performance Review session.' },
  { emoji: '⚠️', text: 'What is the whistleblower protection policy?' },
  { emoji: '🛡️', text: 'Explain the workplace safety guidelines.' },
  { emoji: '👤', text: 'What are the different job roles described in the handbook?' },
];

export function EmptyState({ onSelectPrompt }: Props) {
  return (
    <div className="empty-state" role="main" aria-labelledby="empty-title">
      <div className="empty-hero">
        <div className="empty-logo" aria-hidden="true">
          <span className="empty-logo-icon">📖</span>
        </div>
        <h2 id="empty-title" className="empty-title">Agentic Handbook Assistant</h2>
        <p className="empty-subtitle">
          Ask questions about the employee handbook or book a Performance Review session.
          Answers are grounded in the actual policy document with page citations.
        </p>
      </div>

      <div className="empty-prompts" aria-label="Suggested questions">
        <p className="empty-prompts-label">Try asking:</p>
        <div className="empty-prompts-grid">
          {EXAMPLE_PROMPTS.map(({ emoji, text }) => (
            <button
              key={text}
              type="button"
              className="prompt-chip"
              onClick={() => onSelectPrompt(text)}
              aria-label={`Send: ${text}`}
            >
              <span className="prompt-emoji" aria-hidden="true">{emoji}</span>
              <span className="prompt-text">{text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
