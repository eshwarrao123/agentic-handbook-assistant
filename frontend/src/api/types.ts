/**
 * API types mirroring docs/API_CONTRACT.md
 */

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

export interface ApiErrorDetails {
  code: string;
  message: string;
  retryable: boolean;
  request_id?: string;
  details?: unknown;
}
