/**
 * API types mirroring docs/API_CONTRACT.md §4 and §9.
 */

// --- Health Diagnostics Types ---

export interface VectorStoreHealth {
  status: string;
  collection: string;
  chunk_count: number;
}

export interface CheckpointerHealth {
  status: string;
  backend: string;
}

export interface LLMHealth {
  status: string;
  provider: string;
}

export interface ComponentsHealth {
  vector_store: VectorStoreHealth;
  checkpointer: CheckpointerHealth;
  llm: LLMHealth;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'unavailable';
  version: string;
  time: string;
  components: ComponentsHealth;
}

// --- Chat and Booking Types (API_CONTRACT §9) ---

export type BookingStatus = 'none' | 'collecting' | 'awaiting_slot' | 'confirmed' | 'cancelled';

export interface Slot {
  slot_id: string;
  start: string;
  label: string;
}

export interface SlotsResponse {
  service_type: string;
  timezone: string;
  total_available: number;
  slots: Slot[];
}

export interface Citation {
  document: string;
  title: string;
  page: number;
  snippet: string;
  chunk_id: string;
}

export interface Confirmation {
  reference: string;
  slot: Slot;
  full_name: string;
  email: string;
  service_type: string;
  simulated: true;
}

export interface BookingSnapshot {
  status: BookingStatus;
  service_type: string | null;
  full_name: string | null;
  email: string | null;
  offered_slots: Slot[];
  confirmation: Confirmation | null;
}

export interface AgentInfo {
  status: 'ok' | 'degraded';
  error_code: string | null;
  intents: ('booking' | 'faq')[];
  route: string[];
}

export interface ChatRequest {
  thread_id?: string | null;
  message: string;
}

export interface ChatResponse {
  thread_id: string;
  is_new_thread: boolean;
  reply: {
    message_id: string;
    role: 'assistant';
    content: string;
    citations: Citation[];
    created_at: string;
  };
  booking: BookingSnapshot;
  agent: AgentInfo;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    request_id: string;
    details: unknown;
  };
}
