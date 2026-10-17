/**
 * API client for interacting with the FastAPI backend.
 * Uses relative /api paths by default to leverage the Vite dev server proxy.
 */

import type { HealthResponse } from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export class ApiClientError extends Error {
  public status?: number;
  public details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Fetch health diagnostic data from GET /api/health.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const url = `${BASE_URL}/api/health`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      let errorDetails: unknown = null;
      try {
        errorDetails = await response.json();
      } catch {
        // Response body might not be JSON
      }
      throw new ApiClientError(
        `Backend returned HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorDetails
      );
    }

    const data: HealthResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    const message = error instanceof Error ? error.message : 'Unknown network failure';
    throw new ApiClientError(
      `Failed to connect to backend at ${url}. ${message}`,
      undefined,
      error
    );
  }
}
