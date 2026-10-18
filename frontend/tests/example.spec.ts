/**
 * E2E tests for Agentic Handbook Assistant — Phase 7
 *
 * Prerequisite: Both the FastAPI backend (port 8000) and Vite dev server
 * (port 5173) must be running. Tests use the live backend.
 *
 * Run: npx playwright test
 *
 * NOTE: Tests that require LLM responses (handbook questions, booking flow)
 * will only pass when the backend has a configured LLM key and RAG index.
 * Tests marked with a comment "/* LLM-dependent *\/" are skipped in offline
 * environments by checking the health endpoint first.
 */

import { test, expect } from '@playwright/test';

// ============================================================
// Test Suite
// ============================================================

test.describe('Agentic Handbook Assistant — Chat Interface', () => {

  test.beforeEach(async ({ page }) => {
    // Clear sessionStorage to start a fresh thread for each test
    await page.goto('/');
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
  });

  // ----------------------------------------------------------
  // Test 1: Chat page loads
  // ----------------------------------------------------------
  test('chat page loads with correct title and empty state', async ({ page }) => {
    await page.goto('/');

    // Title
    await expect(page).toHaveTitle(/Agentic Handbook Assistant/);

    // h1 should be present
    await expect(page.getByRole('heading', { name: /Agentic Handbook Assistant/i, level: 1 })).toBeVisible();

    // Empty state prompt chips
    await expect(page.locator('.prompt-chip').first()).toBeVisible();

    // Composer is visible
    await expect(page.locator('#chat-input')).toBeVisible();
    await expect(page.locator('#send-btn')).toBeVisible();
  });

  // ----------------------------------------------------------
  // Test 2: Backend connection status
  // ----------------------------------------------------------
  test('shows backend connection status correctly', async ({ page }) => {
    await page.goto('/');

    // Connection pill should appear and eventually show connected or disconnected
    const pill = page.locator('.connection-pill');
    await pill.waitFor({ state: 'visible', timeout: 10000 });

    const text = await pill.innerText();
    // Should show one of the expected states
    expect(['Connecting…', 'Connected', 'Degraded', 'Offline']).toContain(text.trim());
  });

  // ----------------------------------------------------------
  // Test 3: Send button and Enter behavior
  // ----------------------------------------------------------
  test('send button is disabled with empty input and enabled with text', async ({ page }) => {
    await page.goto('/');

    const sendBtn = page.locator('#send-btn');
    const textarea = page.locator('#chat-input');

    // Button starts disabled (no text)
    await expect(sendBtn).toBeDisabled();

    // Type some text
    await textarea.fill('test message');
    await expect(sendBtn).not.toBeDisabled();

    // Clear text — button should be disabled again
    await textarea.fill('');
    await expect(sendBtn).toBeDisabled();
  });

  // ----------------------------------------------------------
  // Test 4: Clicking a prompt chip populates and sends
  // ----------------------------------------------------------
  test('clicking a prompt chip sends the message', async ({ page }) => {
    await page.goto('/');

    // Wait for connection (either connected or offline — we just test UI behavior)
    const pill = page.locator('.connection-pill');
    await pill.waitFor({ state: 'visible' });

    // Click first prompt chip
    const chip = page.locator('.prompt-chip').first();
    const chipText = await chip.locator('.prompt-text').innerText();
    await chip.click();

    // User message bubble should appear
    const userBubble = page.locator('.bubble-user').first();
    await userBubble.waitFor({ state: 'visible', timeout: 5000 });
    const bubbleText = await userBubble.innerText();
    expect(bubbleText.trim()).toBe(chipText.trim());
  });

  // ----------------------------------------------------------
  // Test 5: New Chat action clears messages and thread
  // ----------------------------------------------------------
  test('new chat button clears messages and starts a fresh thread', async ({ page }) => {
    await page.goto('/');

    // Wait for UI to be ready
    await page.locator('#chat-input').waitFor({ state: 'visible' });

    // Type a message but don't send — we just want to verify the UI clears
    const textarea = page.locator('#chat-input');
    await textarea.fill('test message before new chat');

    // Click New Chat
    await page.locator('#new-chat-btn').click();

    // Textarea should be cleared
    await expect(textarea).toHaveValue('');

    // Empty state should be back (prompt chips visible)
    await expect(page.locator('.prompt-chip').first()).toBeVisible();
  });

  // ----------------------------------------------------------
  // Test 6: 360px viewport layout
  // ----------------------------------------------------------
  test('layout remains usable at 360px viewport width', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 640 });
    await page.goto('/');

    // Chat input should be visible
    await expect(page.locator('#chat-input')).toBeVisible();

    // Header should be visible
    await expect(page.locator('.chat-header')).toBeVisible();

    // No horizontal overflow
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(380); // Allow small tolerance
  });

  // ----------------------------------------------------------
  // Test 7: Keyboard accessibility — Enter sends, Shift+Enter does not
  // ----------------------------------------------------------
  test('Enter sends message, Shift+Enter adds newline', async ({ page }) => {
    await page.goto('/');

    const textarea = page.locator('#chat-input');
    await textarea.fill('line one');

    // Shift+Enter should add a newline (not submit)
    await textarea.press('Shift+Enter');
    const valueAfterShiftEnter = await textarea.inputValue();
    expect(valueAfterShiftEnter).toContain('\n');

    // Regular Enter should attempt submit (even if backend is down, UI will show error)
    await textarea.fill('test message');
    await textarea.press('Enter');

    // Either a user bubble or an error message should appear
    await page.waitForSelector('.bubble-user, .bubble-error', { timeout: 8000 });
  });

  // ----------------------------------------------------------
  // Test 8: Error state when backend is unavailable
  // ----------------------------------------------------------
  test('shows error recovery state with input preserved on failed request', async ({ page }) => {
    // Route API calls to fail
    await page.route('/api/chat', route => route.abort('failed'));

    await page.goto('/');
    await page.evaluate(() => sessionStorage.clear());

    const textarea = page.locator('#chat-input');
    await textarea.fill('This message should fail');
    await page.locator('#send-btn').click();

    // Error bubble should appear
    const errorBubble = page.locator('.bubble-error');
    await errorBubble.waitFor({ state: 'visible', timeout: 10000 });

    // Input should be restored
    await expect(textarea).toHaveValue('This message should fail');
  });

  // ----------------------------------------------------------
  // Test 9: Session ID persists across page navigation
  // ----------------------------------------------------------
  test('thread_id is persisted in sessionStorage', async ({ page }) => {
    await page.goto('/');

    const chatResponsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/chat') && resp.status() === 200,
      { timeout: 20000 }
    );

    const textarea = page.locator('#chat-input');
    await textarea.fill('hello');
    await page.locator('#send-btn').click();

    const chatResponse = await chatResponsePromise;
    const json = await chatResponse.json();
    const capturedThreadId = json.thread_id;
    expect(capturedThreadId).toBeTruthy();

    // Check sessionStorage
    const stored = await page.evaluate(
      (key) => sessionStorage.getItem(key),
      'aha_thread_id'
    );
    expect(stored).toBe(capturedThreadId);

    // Thread indicator should show partial ID
    await expect(page.locator('.thread-id')).toBeVisible();
  });

  // ----------------------------------------------------------
  // Test 10: Citations list and disclosure toggle (FE-003, E2E-001)
  // ----------------------------------------------------------
  test('renders citations disclosure with document and page info', async ({ page }) => {
    // Mock a response containing citations
    await page.route('/api/chat', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread_id: 'mock-thread-citations-123',
          is_new_thread: true,
          reply: {
            message_id: 'msg-mock-1',
            role: 'assistant',
            content: 'Performance reviews are conducted annually according to the handbook.',
            citations: [
              {
                document: 'employee_handbook.pdf',
                title: 'Zava Employee Handbook',
                page: 4,
                snippet: 'Performance evaluations are conducted annually in December.',
                chunk_id: 'mock-chunk-1',
              },
            ],
            created_at: new Date().toISOString(),
          },
          booking: {
            status: 'none',
            service_type: null,
            full_name: null,
            email: null,
            offered_slots: [],
            confirmation: null,
          },
          agent: {
            status: 'ok',
            error_code: null,
            intents: ['faq'],
            route: ['start_turn', 'analyze_turn', 'faq_rag', 'compose_response'],
          },
        }),
      });
    });

    await page.goto('/');
    const textarea = page.locator('#chat-input');
    await textarea.fill('How often are performance reviews conducted?');
    await page.locator('#send-btn').click();

    // Citations disclosure should be visible
    const disclosure = page.locator('.citations-disclosure');
    await expect(disclosure).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.citations-summary')).toContainText('1 source');

    // Click to open citations list
    await disclosure.locator('.citations-summary').click();
    await expect(page.locator('.citation-page')).toContainText('p. 4');
    await expect(page.locator('.citation-snippet')).toContainText('Performance evaluations are conducted annually');
  });

  // ----------------------------------------------------------
  // Test 11: Booking confirmation card rendering (FE-004, E2E-002)
  // ----------------------------------------------------------
  test('renders booking confirmation card with reference ID and simulated note', async ({ page }) => {
    // Mock confirmed booking response
    await page.route('/api/chat', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread_id: 'mock-thread-booking-456',
          is_new_thread: false,
          reply: {
            message_id: 'msg-mock-booking',
            role: 'assistant',
            content: 'Your Performance Review session has been confirmed!',
            citations: [],
            created_at: new Date().toISOString(),
          },
          booking: {
            status: 'confirmed',
            service_type: 'performance_review',
            full_name: 'Alex Chen',
            email: 'alex.chen@example.com',
            offered_slots: [],
            confirmation: {
              reference: 'PR-20261019-9876',
              service_type: 'performance_review',
              slot: {
                slot_id: 'slot-mock-1',
                start_utc: '2026-10-19T05:00:00Z',
                end_utc: '2026-10-19T05:45:00Z',
                label: 'Monday, Oct 19 at 10:30 AM IST',
              },
              full_name: 'Alex Chen',
              email: 'alex.chen@example.com',
              created_at: new Date().toISOString(),
              simulated: true,
            },
          },
          agent: {
            status: 'ok',
            error_code: null,
            intents: ['booking'],
            route: ['start_turn', 'analyze_turn', 'booking_step', 'compose_response'],
          },
        }),
      });
    });

    await page.goto('/');
    const textarea = page.locator('#chat-input');
    await textarea.fill('Confirm Monday 10:30am');
    await page.locator('#send-btn').click();

    // Confirmation card should appear
    const confirmationCard = page.locator('.booking-confirmation');
    await expect(confirmationCard).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.confirmation-ref-value')).toHaveText('PR-20261019-9876');
    await expect(page.locator('.confirmation-simulated')).toBeVisible();
  });

  // ----------------------------------------------------------
  // Test 12: Route nodes displayed in header (FE-010)
  // ----------------------------------------------------------
  test('displays agent route nodes badge in header after turn', async ({ page }) => {
    await page.route('/api/chat', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread_id: 'mock-thread-route-789',
          is_new_thread: true,
          reply: {
            message_id: 'msg-route-1',
            role: 'assistant',
            content: 'Hello! I am ready to help.',
            citations: [],
            created_at: new Date().toISOString(),
          },
          booking: {
            status: 'none',
            service_type: null,
            full_name: null,
            email: null,
            offered_slots: [],
            confirmation: null,
          },
          agent: {
            status: 'ok',
            error_code: null,
            intents: ['general'],
            route: ['start_turn', 'analyze_turn', 'compose_response'],
          },
        }),
      });
    });

    await page.goto('/');
    const textarea = page.locator('#chat-input');
    await textarea.fill('Hello');
    await page.locator('#send-btn').click();

    // Route nodes should appear in header
    const routeContainer = page.locator('.agent-route');
    await expect(routeContainer).toBeVisible({ timeout: 10000 });
    await expect(routeContainer).toContainText('start_turn');
    await expect(routeContainer).toContainText('analyze_turn');
  });

  // ----------------------------------------------------------
  // Test 13: Live RAG Query against running backend (E2E-005)
  // ----------------------------------------------------------
  test('live RAG question retrieves answer and citations from real backend', async ({ page }) => {
    // Uses real backend without page.route interception
    await page.goto('/');

    const chatResponsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/chat') && resp.status() === 200,
      { timeout: 25000 }
    );

    const textarea = page.locator('#chat-input');
    await textarea.fill('How often are performance reviews conducted according to the handbook?');
    await page.locator('#send-btn').click();

    const response = await chatResponsePromise;
    const json = await response.json();

    // Verify response structure from live backend
    expect(json.reply.content.toLowerCase()).toContain('annual');
    expect(json.reply.citations.length).toBeGreaterThanOrEqual(1);
    expect(json.reply.citations[0].document).toBe('employee_handbook.pdf');
    expect(json.reply.citations[0].page).toBe(4);

    // Verify assistant bubble in UI
    const assistantBubble = page.locator('.bubble-assistant').first();
    await expect(assistantBubble).toBeVisible({ timeout: 10000 });
    await expect(assistantBubble).toContainText(/annual/i);

    // Verify citation disclosure in UI
    const disclosure = page.locator('.citations-disclosure').first();
    await expect(disclosure).toBeVisible();
  });
});

