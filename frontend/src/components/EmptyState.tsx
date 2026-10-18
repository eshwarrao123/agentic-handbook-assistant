/**
 * EmptyState — Editorial introduction showing handbook Q&A and booking capabilities
 */

import { BookOpen, Calendar, FileText, HelpCircle, Shield, Users } from 'lucide-react';
import './EmptyState.css';

interface Props {
  onSelectPrompt: (prompt: string) => void;
}

const HANDBOOK_PROMPTS = [
  { icon: FileText, text: 'How often are performance reviews conducted?' },
  { icon: Shield, text: 'What does the handbook say about data security?' },
  { icon: HelpCircle, text: 'What is the whistleblower protection policy?' },
  { icon: Users, text: 'What are the different job roles described in the handbook?' },
];

const BOOKING_PROMPT = 'I need to book a Performance Review session.';

export function EmptyState({ onSelectPrompt }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-intro">
        <div className="empty-welcome">Employee Resources</div>
        <h1 className="empty-title">Handbook Assistant</h1>
        <p className="empty-description">
          Search the employee handbook with cited answers from the actual policy document,
          or schedule a Performance Review appointment with available time slots.
        </p>
      </div>

      <div className="empty-sections">
        {/* Handbook Q&A Section */}
        <section className="empty-section" aria-labelledby="handbook-section">
          <div className="section-header">
            <BookOpen className="section-icon knowledge" aria-hidden="true" />
            <div className="section-info">
              <h2 id="handbook-section" className="section-title">Ask About the Handbook</h2>
              <p className="section-subtitle">
                Get answers grounded in the employee handbook with page citations
              </p>
            </div>
          </div>
          <div className="section-prompts">
            {HANDBOOK_PROMPTS.map(({ icon: Icon, text }) => (
              <button
                key={text}
                type="button"
                className="prompt-button"
                onClick={() => onSelectPrompt(text)}
                aria-label={`Ask: ${text}`}
              >
                <Icon className="prompt-icon" aria-hidden="true" />
                <span>{text}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Booking Section */}
        <section className="empty-section" aria-labelledby="booking-section">
          <div className="section-header">
            <Calendar className="section-icon booking" aria-hidden="true" />
            <div className="section-info">
              <h2 id="booking-section" className="section-title">Schedule an Appointment</h2>
              <p className="section-subtitle">
                Book a Performance Review session with available time slots
              </p>
            </div>
          </div>
          <div className="section-prompts">
            <button
              type="button"
              className="prompt-button"
              onClick={() => onSelectPrompt(BOOKING_PROMPT)}
              aria-label={`Request: ${BOOKING_PROMPT}`}
            >
              <Calendar className="prompt-icon" aria-hidden="true" />
              <span>{BOOKING_PROMPT}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
