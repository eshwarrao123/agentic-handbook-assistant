/**
 * BookingPanel — renders booking state from the API response.
 * All data comes from booking: BookingSnapshot; nothing is invented on the frontend.
 */

import type { BookingSnapshot } from '../api/types';
import './BookingPanel.css';

interface Props {
  booking: BookingSnapshot;
}

export function BookingPanel({ booking }: Props) {
  if (booking.status === 'none') return null;

  return (
    <div className={`booking-panel booking-${booking.status}`} aria-label="Booking status">
      <div className="booking-header">
        <StatusBadge status={booking.status} />
        {booking.service_type && (
          <span className="booking-service">
            {formatServiceType(booking.service_type)}
          </span>
        )}
      </div>

      {/* Attendee info when collected */}
      {(booking.full_name || booking.email) && booking.status !== 'confirmed' && (
        <div className="booking-attendee">
          {booking.full_name && (
            <span className="booking-field">
              <span className="booking-field-label">Name:</span>
              {booking.full_name}
            </span>
          )}
          {booking.email && (
            <span className="booking-field">
              <span className="booking-field-label">Email:</span>
              {booking.email}
            </span>
          )}
        </div>
      )}

      {/* Offered slots */}
      {booking.offered_slots.length > 0 && (
        <div className="booking-slots">
          <p className="booking-slots-label">Available slots:</p>
          <ol className="booking-slots-list">
            {booking.offered_slots.map((slot, i) => (
              <li key={slot.slot_id} className="booking-slot-item">
                <span className="slot-num">{i + 1}.</span>
                <span className="slot-label">{slot.label}</span>
              </li>
            ))}
          </ol>
          <p className="booking-slots-hint">
            Reply with the number or describe the day and time.
          </p>
        </div>
      )}

      {/* Confirmation card */}
      {booking.status === 'confirmed' && booking.confirmation && (
        <div className="booking-confirmation">
          <div className="confirmation-ref">
            <span className="confirmation-ref-label">Reference</span>
            <span className="confirmation-ref-value">{booking.confirmation.reference}</span>
          </div>
          <div className="confirmation-details">
            <div className="confirmation-row">
              <span className="confirmation-label">When</span>
              <span className="confirmation-value">{booking.confirmation.slot.label}</span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Name</span>
              <span className="confirmation-value">{booking.confirmation.full_name}</span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Email</span>
              <span className="confirmation-value">{booking.confirmation.email}</span>
            </div>
          </div>
          {booking.confirmation.simulated && (
            <p className="confirmation-simulated">
              ℹ️ Simulated booking — no real calendar entry was created.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: BookingSnapshot['status'] }) {
  const labels: Record<BookingSnapshot['status'], string> = {
    none: '',
    collecting: 'Collecting details',
    awaiting_slot: 'Choose a slot',
    confirmed: '✓ Confirmed',
    cancelled: 'Cancelled',
  };
  return (
    <span className={`booking-status-badge badge-${status}`}>
      {labels[status]}
    </span>
  );
}

function formatServiceType(raw: string): string {
  return raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
