# AI Engineering Log — Agentic Handbook Assistant

Related: `ASSESSMENT_TRACEABILITY.md` (AR-007, AR-062, AR-063), `IMPLEMENTATION_PLAN.md` (log habits per phase), `LEARNING_ROADMAP.md` (Q-23).

This file satisfies the assessment's mandatory *AI Engineering Log* (brief §2): (1) list all AI tools used; (2) document specific instances of broken or hallucinated AI logic and how you identified, diagnosed and resolved them. A condensed version goes into `README.md` (decision D-20).

---

## 0. Rules for this log (read before writing)

1. **Only record what actually happened.** Do not invent tools, model names, failures, hallucinations, test results or debugging stories. A short honest log beats an impressive fake one.
2. **Write entries while the evidence exists** — paste the error text, failing test name, `get_state` dump or diff immediately. Reconstructing later from memory invites fiction.
3. **Model names exactly as the tool shows them** (copy from the UI/selector). If you don't know, write "unknown".
4. **Every incident needs evidence** (output/test/state dump) and a **verification** (test ID + result after the fix).
5. If no AI-generated defect occurred, say so in §4 and fill §8 (near-misses caught in review) with real examples. Do not manufacture an incident to satisfy the requirement.
6. Mark planning-stage claims as *planning claims* until you re-verify them yourself (§6).

**Project timing (fill in):** assessment dispatched at: `____` · first commit: `____` · submission: `____` (supports AR-009)

---

## 1. AI tools and models actually used

| # | Tool | Model/version as displayed | Mode (chat / agent / autocomplete) | Phase(s) | Used for | First used (date/time) |
|---|---|---|---|---|---|---|
| T-01 | Claude Web | Claude 3.7 Sonnet | Chat | Planning | Initial drafting of docs/ specification suite | 2026-10-16 |
| T-02 | Google Antigravity IDE | Gemini 3.8 Flash (High) | Agent (Pair programming) | Phase 1 | Foundation, FastAPI backend, React frontend, config hygiene, tests | 2026-10-17 13:06 IST |

---

## 2. Task-level usage log

| # | Date | Phase | Tool/model (T-xx) | Task given to the AI | Output used? (yes / partly / no) | Entry refs (§3/§4) |
|---|---|---|---|---|---|---|
| U-01 | 2026-10-17 | Phase 1 | T-02 | Implement Phase 1: FastAPI health check, Vite proxy connectivity screen, repo hygiene, tests, and learning notes | Yes | S-01, S-02, INC-01, INC-02, INC-03 |
| U-02 | 2026-10-17 | Phase 2 | T-02 | Implement Phase 2: LangGraph StateGraph, merge_booking reducer, routing pure functions, nodes, ChatService, POST /api/chat shell, error envelope, and unit/graph/API tests | Yes | S-03, INC-04, INC-05 |
| U-03 | 2026-10-18 | Phase 7 | T-02 | Implement Phase 7: Complete React chat interface, citations disclosure, booking panel, thread management, error preservation, Playwright E2E suite, and browser verification | Yes | S-04, INC-10, INC-11 |

---

## 3. Suggestions accepted, rejected or modified

| # | Phase | Tool (T-xx) | AI suggestion (summary) | Decision | Why (your reasoning) | Evidence/link |
|---|---|---|---|---|---|---|
| S-01 | Phase 1 | T-02 | Use `pytest-asyncio` with `httpx.AsyncClient` fixture for health test | Modified | `pytest-asyncio` 1.4.0 failed on Python 3.14 with `AssertionError` in `setup()`. Switched to FastAPI's built-in synchronous `TestClient` (backed by `httpx`), eliminating event loop runner bugs and executing in 0.17s. | INC-01; `backend/tests/conftest.py` |
| S-02 | Phase 1 | T-02 | Install Tailwind CSS v4 Vite plugin | Rejected | Followed decision D-15 (plain CSS fallback). Vanilla CSS with CSS custom properties avoids build friction on Vite 6 / Node 24 and keeps dependencies minimal for Phase 1. | `frontend/src/App.css` |
| S-03 | Phase 2 | T-02 | Pass existing booking state into `ainvoke` during multi-turn chat in `ChatService` | Rejected | Followed `TECHNICAL_DESIGN.md` §5.4 (Graph Input Rule). Passing `booking` in graph input clobbers checkpointed progress and bypasses reducer mechanics. Only `{"messages": [HumanMessage(...)]}` is passed. | `backend/app/services/chat_service.py` |
| S-04 | Phase 7 | T-02 | Reconstruct conversation messages from server thread history on UI reload | Rejected | Followed API contract and architecture: backend is authoritative. The frontend only maintains sessionStorage thread_id for continuity, avoiding state drift or complex client-side reconciliation. | `frontend/src/components/ChatPage.tsx` |


---

## 4. Incorrect, hallucinated or broken AI logic found

### INC-01 — pytest-asyncio 1.4.0 fixture resolution failure on Python 3.14
- Date / Phase: 2026-10-17 / Phase 1 — Project Foundation
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Create automated backend tests for `GET /api/health`
- What the AI produced (the faulty part): `backend/tests/conftest.py` with `@pytest.fixture async def async_client()`
- Symptom: Pytest threw `AssertionError` at `setup()` in `pytest_asyncio/plugin.py:558` and reported `requested an async fixture 'async_client', with no plugin or hook that handled it`
- Diagnostic evidence:
  ```
  ERROR at setup of test_health_check_returns_ok_schema
  'test_health_check_returns_ok_schema' requested an async fixture 'async_client', with no plugin or hook that handled it.
  AssertionError in C:\Python314\Lib\site-packages\pytest_asyncio\plugin.py:558: return super().setup()
  ```
- How I diagnosed it: Ran `python -m pytest -v` against the generated async fixture on Python 3.14.6. Python 3.14 internal coroutine inspection deprecations broke `pytest-asyncio`'s loop factory setup.
- Root cause: `pytest-asyncio` 1.4.0 has compatibility issues with Python 3.14's async fixture runner lifecycle when resolving async test fixtures.
- Correction: Replaced async fixture with Starlette/FastAPI's synchronous `TestClient(app)` fixture in `backend/tests/conftest.py` and updated `test_health.py` to synchronous test functions.
- Verification: `python -m pytest -v` passed all 3 tests in 0.17s.
- Regression protection: `backend/tests/conftest.py` uses synchronous `TestClient`.
- Lesson: For pure HTTP endpoint contract testing, synchronous `TestClient` is faster, simpler, and immune to async runner version incompatibilities.
- Related: `API-001`, `API_CONTRACT.md` §4, `TEST_PLAN.md` §1.

### INC-02 — TypeScript TS1484 verbatimModuleSyntax import error
- Date / Phase: 2026-10-17 / Phase 1 — Project Foundation
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement API client and React UI in Vite React-TS
- What the AI produced (the faulty part): `import { HealthResponse } from './types'` in `frontend/src/api/client.ts` and `frontend/src/App.tsx`
- Symptom: `npm run build` failed with `error TS1484: 'HealthResponse' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.`
- Diagnostic evidence:
  ```
  src/api/client.ts(6,10): error TS1484: 'HealthResponse' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
  src/App.tsx(3,10): error TS1484: 'HealthResponse' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
  ```
- How I diagnosed it: Inspected `tsconfig.app.json` in the Vite template; found `"verbatimModuleSyntax": true`.
- Root cause: Under `verbatimModuleSyntax`, TypeScript forbids importing pure types/interfaces without the `type` keyword because it preserves the exact import syntax unless explicitly marked for erasure.
- Correction: Changed imports to `import type { HealthResponse } from ...` in both `client.ts` and `App.tsx`.
- Verification: `npm run build` completed successfully in 161ms.
- Regression protection: TypeScript type-check runs as part of `npm run build`.
- Lesson: Always use `import type` for pure interfaces and types in modern Vite TypeScript projects.
- Related: `AR-036`.

### INC-03 — oxlint set-state-in-effect cascading render warning
- Date / Phase: 2026-10-17 / Phase 1 — Project Foundation
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Check code quality with `npm run lint`
- What the AI produced (the faulty part): Synchronously invoking `checkConnection()` inside `useEffect` on mount, which called `setConnectionState('loading')`
- Symptom: Linter warning: `react(set-state-in-effect): Calling setState synchronously within an effect can trigger cascading renders`
- Diagnostic evidence:
  ```
  oxlint found 1 warning: Avoid calling setState() directly within an effect
  ```
- How I diagnosed it: Inspected `App.tsx`; the component state was already initialized to `'loading'` via `useState('loading')`, so calling a synchronous setter immediately on mount causes an unnecessary extra render cycle.
- Root cause: Calling synchronous state setters inside `useEffect` on mount triggers React cascading renders.
- Correction: Refactored `useEffect` to execute an async `initialCheck()` function with an unmount cleanup cancellation flag (`let ignore = false;`), ensuring state setters are called only after the async promise resolves.
- Verification: `npm run lint` reported 0 warnings and 0 errors across all 5 files.
- Regression protection: `oxlint` runs on pre-commit/build checks.
- Lesson: State initialization belongs in `useState()`, and `useEffect` fetches should update state asynchronously when responses arrive.
- Related: `FE-001`.

### INC-04 — Substring keyword collision in analyze_turn causing false booking activation
- Date / Phase: 2026-10-17 / Phase 2 — LangGraph Foundation and Chat API Shell
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement deterministic development router in `app/graph/nodes/analyze_turn.py`
- What the AI produced (the faulty part): Intent detection using substring matching:
  ```python
  if any(k in user_lower for k in ("book", "schedule", "performance review", ...)):
      booking_requested = True
      intents.append("booking")
  ```
- Symptom: In `backend/tests/graph/test_graph_foundation.py::test_thread_isolation`, sending `"What is the employee handbook policy?"` on Thread B unexpectedly transitioned booking status to `collecting`.
- Diagnostic evidence:
  ```
  FAILED tests/graph/test_graph_foundation.py::test_thread_isolation - AssertionError: assert 'collecting' == 'none'
  ```
- How I diagnosed it: Inspected the input string `"What is the employee handbook policy?"`. The word `"handbook"` contains the substring `"book"`. Naive substring search evaluated to `True`, inappropriately classifying an FAQ handbook query as a booking request.
- Root cause: Missing regex word boundaries (`\b`) allowed the subword `"book"` inside `"handbook"` to trigger booking mode.
- Correction: Replaced naive substring checks with compiled word-boundary regular expressions:
  ```python
  BOOKING_PATTERN = re.compile(r"\b(book|booking|schedule|performance review|appointment|session|reserve)\b", re.IGNORECASE)
  ```
- Verification: `python -m pytest -v tests/graph/test_graph_foundation.py` passed all 4 tests cleanly, confirming Thread B remained at `status: "none"`.
- Regression protection: Added regression test `test_thread_isolation` asserting that pure FAQ questions referencing "handbook" never mutate booking status.
- Lesson: Never use raw substring matching for intent keywords; always use word boundary regex patterns (`\b`) or structured token classifiers.
- Related: `GR-013`, `TECHNICAL_DESIGN.md` §6.1.

### INC-05 — Starlette TestClient re-raising server exceptions during HTTP 500 boundary test
- Date / Phase: 2026-10-17 / Phase 2 — LangGraph Foundation and Chat API Shell
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement and test HTTP 500 error envelope for unhandled exceptions (API-011)
- What the AI produced (the faulty part): Standard `client.post("/api/chat", json=...)` with patched `RuntimeError`
- Symptom: Test runner aborted with unhandled `RuntimeError: Secret database failed` instead of asserting the HTTP 500 error envelope response.
- Diagnostic evidence:
  ```
  FAILED tests/api/test_chat.py::test_forced_internal_exception_returns_500_envelope
  RuntimeError: Secret database failed
  ```
- How I diagnosed it: Inspected Starlette's `TestClient` implementation. By default, `TestClient(app)` sets `raise_server_exceptions=True`, which causes ASGI exceptions to be re-raised directly in the test thread rather than formatted as HTTP 500 responses.
- Root cause: Default `raise_server_exceptions=True` in Starlette's test client intercepts unhandled exceptions before test assertions can inspect the HTTP 500 JSON envelope.
- Correction: Updated `RequestIdMiddleware` in `backend/app/main.py` with a `try/except` block to directly catch any uncaught exceptions and invoke `generic_exception_handler`, and instantiated `TestClient(app, raise_server_exceptions=False)` for the boundary test.
- Verification: `python -m pytest -v tests/api/test_chat.py` passed all 6 tests in 0.53s, including `test_forced_internal_exception_returns_500_envelope`.
- Regression protection: `test_forced_internal_exception_returns_500_envelope` strictly validates that HTTP 500 is returned with `error.code == "INTERNAL_ERROR"` and no stack traces leak.
- Lesson: For negative testing of 500 server errors in FastAPI/Starlette, always set `raise_server_exceptions=False` on the test client.
- Related: `API-011`, `API_CONTRACT.md` §2, `TEST_PLAN.md` §6.

### INC-06 — Global PYTHONPATH pointing to Python 3.13 site-packages causing ModuleNotFoundError in Python 3.14
- Date / Phase: 2026-10-18 / Phase 3 — RAG Implementation
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Ingest handbook and initialize ChromaDB persistent client
- What the AI produced (the faulty part): Standard `import chromadb` and `chromadb.PersistentClient()`
- Symptom: Command failed with `ModuleNotFoundError: No module named 'rpds.rpds'` originating in `jsonschema` inside `chromadb`.
- Diagnostic evidence:
  ```
  File "C:\Python313\Lib\site-packages\referencing\_core.py", line 9, in <module>
    from rpds import HashTrieMap, HashTrieSet, List
  File "C:\Python313\Lib\site-packages\rpds\__init__.py", line 1, in <module>
    from .rpds import *
  ModuleNotFoundError: No module named 'rpds.rpds'
  ```
- How I diagnosed it: Inspected `sys.path` and environment variables. Discovered `$env:PYTHONPATH` was set to `C:\Python313\Lib\site-packages`. Python 3.14 was loading C-extension wheels compiled for Python 3.13 ahead of its own standard site-packages.
- Root cause: Cross-Python version contamination via system `PYTHONPATH` leaked Python 3.13 compiled wheels into the Python 3.14 process.
- Correction: Added defensive `sys.path` cleansing at the entry points of `app/__init__.py`, `tests/conftest.py`, and `app/rag/ingest.py` to prune out `Python313` directories when executing in Python 3.14.
- Verification: Running `import app; import chromadb` and `python -m pytest` succeeded without error.
- Regression protection: `sys.path` filtering runs automatically before ChromaDB imports.
- Lesson: On developer machines with multiple Python versions installed, never assume `sys.path` is uncontaminated by global environment variables; sanitize `sys.path` early.
- Related: `V-01`, `V-08`, `TECHNICAL_DESIGN.md` §3.

### INC-07 — OfflineLLMGateway inspecting only top passage instead of searching across top-k retrieved chunks
- Date / Phase: 2026-10-18 / Phase 3 — RAG Implementation
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement grounded generation in `faq_rag` and offline gateway
- What the AI produced (the faulty part): `OfflineLLMGateway` inspecting only `top_passage = passages[0]` for key topic phrases.
- Symptom: `test_per_turn_isolation` failed with `AssertionError: assert 'conducted annually' in state_t1['reply_parts'][0]`.
- Diagnostic evidence:
  ```
  FAILED tests/graph/test_graph_foundation.py::test_per_turn_isolation
  AssertionError: assert 'conducted annually' in 'During the review, your supervisor will discuss your performance...'
  ```
- How I diagnosed it: Inspected retrieved chunks for query `"How often are performance reviews conducted according to the handbook?"`. All 3 retrieved chunks were on Page 4 (`p4-c1` dist 0.442, `p4-c2` dist 0.453, `p4-c0` dist 0.461). `p4-c0` contained `"conducted annually"`, but `passages[0]` was `p4-c1`.
- Root cause: Checking only `passages[0]` ignored relevant information present in subsequent retrieved top-k chunks.
- Correction: Refactored `OfflineLLMGateway.answer_from_passages` to scan across all retrieved passages for topic matches before falling back to the first chunk.
- Verification: `python -m pytest tests/graph/test_graph_foundation.py` and `tests/rag/test_rag_pipeline.py` passed 100%.
- Regression protection: `test_per_turn_isolation` and `test_rag_003_performance_review_retrieval` assert page 4 and annual review frequency.
- Lesson: In multi-chunk retrieval, always synthesize across all retrieved top-k passages rather than assuming the closest passage contains every detail.
- Related: `RAG-003`, `RAG-007`, `TECHNICAL_DESIGN.md` §11.4.

### INC-08 — Compound sentence name extraction skipping and NoneType regex start() crash during invalid email collection
- Date / Phase: 2026-10-18 / Phase 5 — Deterministic Booking Engine
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement deterministic attendee name and email extraction in `analyze_turn` for multi-turn booking
- What the AI produced (the faulty part):
  1. Splitting on user_text prefix before email match without sentence boundary checks (`user_text[:email_match.start()]`). In multi-sentence requests such as `"I want to book a review. Jordan Smith (jordan@example.com)"`, `prefix.split()` produced 7 tokens, exceeding the 4-token ceiling and failing to extract the attendee name.
  2. In fallback handling for non-matching email input during `collecting` status, `email_candidate` was assigned raw user text while `email_match` remained `None`. Line 72 then unconditionally accessed `email_match.start()`, raising `AttributeError: 'NoneType' object has no attribute 'start'`.
  3. In `ask_missing_info`, the node unconditionally appended a generic greeting `"Thanks, <Name>. What is your email address?"` even after `booking_update` had already appended a specific invalid email error message to `reply_parts`.
- Symptom: `test_booking_invalid_email_stays_collecting` crashed with `AttributeError: 'NoneType' object has no attribute 'start'`, and upon fixing that, failed assertions because the validation error was buried under the generic prompt.
- Diagnostic evidence:
  ```
  FAILED tests/graph/test_booking_flow.py::test_booking_invalid_email_stays_collecting
  AttributeError: 'NoneType' object has no attribute 'start'
  at app/graph/nodes/analyze_turn.py:72: prefix = user_text[:email_match.start()].strip(" (,\n\t")
  ```
- How I diagnosed it: Traced execution in `analyze_turn.py` and `booking_steps.py`. Confirmed that `email_candidate` truthiness does not guarantee `email_match` is non-null when fallback candidate extraction runs. Traced `reply_parts` reducer in `booking_steps.py` to see duplicate prompt accumulation.
- Root cause:
  1. Prefix slicing assumed single-sentence input instead of checking sentence boundaries (`.rsplit(".", 1)`).
  2. Guard checked `if email_candidate:` instead of `if email_match:` before referencing `email_match.start()`.
  3. Downstream `ask_missing_info` lacked awareness of existing validation messages in `reply_parts`.
- Correction:
  1. Added sentence boundary (`.rsplit(".", 1)`) and `re.split(r"\bfor\s+", prefix)` parsing in `analyze_turn`.
  2. Changed line 70 guard to `if email_match:` and placed cancellation/FAQ checks ahead of email extraction.
  3. Added a check in `ask_missing_info` to detect existing validation messages in `reply_parts` and return them directly without appending generic greetings.
- Verification: `python -m pytest tests/graph/test_booking_flow.py` and the full test suite (`python -m pytest`) passed 60/60 tests (100%).
- Regression protection: `tests/graph/test_booking_flow.py` includes `test_booking_invalid_email_stays_collecting`, `test_booking_partial_name_then_email`, and `test_multiturn_booking_happy_path`.
- Lesson: Never assume a parsed candidate variable guarantees its underlying regex match object exists. Always guard regex object member accesses, and ensure downstream prompt nodes check upstream validation notices.
- Related: `AR-014`, `AR-024`, `TECHNICAL_DESIGN.md` §12.3.

### INC-09 — Compound turn FAQ extraction skewing vector retrieval embeddings in ChromaDB
- Date / Phase: 2026-10-18 / Phase 6 — Durable Persistence & Context Interleaving
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Implement context interleaving for compound messages containing attendee details AND an FAQ question
- What the AI produced (the faulty part): In `analyze_turn.py`, when a user provided a compound message like `"Book a review. Jordan Smith (jordan.smith@example.com). Also how often are performance reviews conducted according to the handbook?"`, `faq_question` was set to the entire raw `user_text`.
- Symptom: `test_interleaving_compound_turn_name_email_and_faq` failed with `AssertionError: assert len(citations) >= 1` (0 citations returned).
- Diagnostic evidence:
  ```
  ChromaDB query for full compound string: distance = 0.5762 > 0.55 threshold (rejected)
  ChromaDB query for isolated question 'Also how often are performance reviews conducted?': distance = 0.4330 < 0.55 threshold (accepted)
  ```
- How I diagnosed it: Traced vector retrieval distances using ChromaDB directly. The non-FAQ prefix `"Book a review. Jordan Smith (jordan.smith@example.com)"` polluted the embedding vector, shifting it away from the handbook performance review section and causing it to exceed the strict 0.55 cosine distance gate.
- Root cause: Assigning the full compound turn text to `faq_question` rather than isolating the question sentence.
- Correction: Added regex sentence splitting in `analyze_turn.py` (`re.split(r"(?<=[.?])\s+", user_text)`) to extract specifically the interrogative / question-sentence segment into `faq_question`.
- Verification: `python -m pytest tests/graph/test_interleaving.py` passed 100% (10/10 tests passed).
- Regression protection: `test_interleaving_compound_turn_name_email_and_faq` verifies that compound turns extract valid citations on page 4.
- Lesson: In conversational agents supporting compound multi-intent turns, never send the full raw message to a vector retriever; parse and extract only the relevant question clause to avoid embedding vector dilution.
- Related: `AR-040`, `AR-025`, `TECHNICAL_DESIGN.md` §7.2.

### INC-10 — Playwright route interception stream consumption causing Response has been disposed
- Date / Phase: 2026-10-18 / Phase 7 — React Chat Interface & Visual Integration
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Write Playwright E2E tests for `sessionStorage` thread_id persistence
- What the AI produced (the faulty part): Intercepting `/api/chat` with `await page.route('/api/chat', async route => { const response = await route.fetch(); const json = await response.json(); ... await route.fulfill({ response }); })`
- Symptom: Playwright threw `Error: apiResponse.json: Response has been disposed`
- Diagnostic evidence:
  ```
  Error: apiResponse.json: Response has been disposed
    at frontend/tests/example.spec.ts:204:35
    > const json = await response.json();
    await route.fulfill({ response });
  ```
- How I diagnosed it: Inspected the Playwright test failure trace. `route.fetch()` produces an `APIResponse` whose response body stream is single-use; calling `.json()` reads and disposes of the underlying stream, causing `route.fulfill({ response })` to fail when it attempts to stream the already-consumed body to the browser.
- Root cause: Body stream consumption during route interception.
- Correction: Replaced the invasive route fetch interception with Playwright's native response observer: `page.waitForResponse(resp => resp.url().includes('/api/chat') && resp.status() === 200)`.
- Verification: Playwright test 9 passed cleanly in 1.0s.
- Regression protection: `tests/example.spec.ts` uses `waitForResponse` for live and passive inspection.
- Lesson: For observing or asserting against live HTTP responses in browser tests, use `page.waitForResponse` rather than consuming streams in `route.fulfill`.
- Related: `AR-051`, `FE-008`.

### INC-11 — Playwright strict mode heading role resolution collision due to duplicated h1 elements
- Date / Phase: 2026-10-18 / Phase 7 — React Chat Interface & Visual Integration
- Tool and model: T-02: Google Antigravity IDE, Gemini 3.8 Flash (High)
- Task given: Run Playwright test suite for chat page load
- What the AI produced (the faulty part): Rendered `<h1>` both in the header banner (`<h1 class="chat-title">`) and inside the hero empty state (`<h1 id="empty-title">`), tested via `page.getByRole('heading', { name: /Agentic Handbook Assistant/i })`
- Symptom: Playwright failed with `strict mode violation: getByRole('heading', { name: /Agentic Handbook Assistant/i }) resolved to 2 elements`
- Diagnostic evidence:
  ```
  strict mode violation: getByRole('heading', { name: /Agentic Handbook Assistant/i }) resolved to 2 elements:
      1) <h1 class="chat-title">Agentic Handbook Assistant</h1>
      2) <h1 id="empty-title" class="empty-title">Agentic Handbook Assistant</h1>
  ```
- How I diagnosed it: Inspected DOM elements and test trace. The page had two top-level headings with identical text.
- Root cause: Lack of semantic heading hierarchy (violating standard SEO/accessibility single-h1 rule) combined with unconstrained Playwright role query.
- Correction: Changed the `EmptyState` component's title from `<h1>` to `<h2>`, and refined the Playwright assertion to specifically assert the page title at `level: 1`: `page.getByRole('heading', { name: /Agentic Handbook Assistant/i, level: 1 })`.
- Verification: Playwright test 1 passed in 1.1s; all 13 tests passed.
- Regression protection: `tests/example.spec.ts` verifies `{ level: 1 }` heading visibility.
- Lesson: Follow SEO best practices with a single `<h1>` per page and child `<h2>` elements; in Playwright tests, always qualify heading role queries with `{ level: N }` when targeting specific semantic levels.
- Related: `AR-050`, `FE-001`.

---

## 5. Architectural and engineering decisions reviewed by me

Record decisions you personally reviewed and can defend. Link to the decision register in `PRD.md` §12 where applicable. Do not copy rationale you do not understand — rewrite it in your own words.

| # | Date | Decision (ID from PRD §12 or new) | Options considered | Why I chose / changed it | Evidence (test, doc read, experiment) |
|---|---|---|---|---|---|
| R-01 | 2026-10-17 | D-15 | Tailwind v4 vs Vanilla CSS | Used Vanilla CSS with CSS custom properties to ensure fast, zero-dependency frontend builds. | `frontend/src/App.css`, `index.css` |
| R-02 | 2026-10-17 | D-08 | Overwrite vs `merge_booking` reducer | Implemented `merge_booking` custom reducer to prevent partial state updates (e.g., updating full_name) from clobbering email or booking status. | UT-003, UT-004, UT-005 in `backend/tests/unit/test_state.py` |
| R-03 | 2026-10-17 | D-05 | In-memory `MemorySaver` vs eager SQLite for Phase 2 | Used `MemorySaver` for Phase 2 graph foundation and API shell testing; kept checkpointer interface injected so `AsyncSqliteSaver` plugs in without graph restructuring. | GR-014, API-005, API-006 in `backend/tests/` |
| R-04 | 2026-10-18 | D-03 / Gate A | RETRIEVAL_MAX_DISTANCE = 0.45 vs 0.55 | Calibrated threshold empirically on 12 answerable queries (min 0.1989, max 0.4721 except hotline, avg 0.4068) and 9 unanswerable queries (min 0.6012, max 0.9594, avg 0.7617). 0.45 was too tight for company values (0.4721) and performance reviews (0.4444). Set threshold to 0.55 to safely accept all valid queries while strictly gating out all unanswerable queries. | `backend/calibrate_retrieval.py`, `tests/rag/test_rag_pipeline.py` (RAG-004, RAG-005) |
| R-05 | 2026-10-18 | D-09 | Deterministic rule-based slot resolution vs LLM slot extraction | Implemented multi-tiered deterministic resolution (exact ID -> option index with out-of-range checks -> day/time regex with ambiguity detection) to ensure the LLM never invents availability or confirms unverified slots. | `tests/unit/test_booking_service.py`, `tests/graph/test_booking_flow.py` |
| R-06 | 2026-10-18 | D-05 | FastAPI Lifespan-managed `AsyncSqliteSaver` vs import-time checkpointer | Managed `AsyncSqliteSaver.from_conn_string()` inside FastAPI `@asynccontextmanager lifespan(app)`, compiling graph once and storing on `app.state.chat_service`. Default singleton uses MemorySaver for fast isolated tests. | `tests/graph/test_persistence.py`, `tests/api/test_chat.py` |

---

## 6. Verification of documentation claims and open V-items

`TECHNICAL_DESIGN.md` §17 lists framework behaviours to confirm. Record what you read and what you found.

| V-item | Source read (official doc/page/version) | Finding | Impact on design | Date |
|---|---|---|---|---|
| V-03 | `langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver` runtime test & inspect | `from_conn_string` is an `@asynccontextmanager` yielding `AsyncSqliteSaver` connected via `aiosqlite`; `setup()` initializes WAL mode and `checkpoints`/`writes` tables; clean lifespan startup/shutdown verified | Validated non-blocking async SQLite persistence without thread-blocking or connection leaks | 2026-10-18 |
| V-08 | ChromaDB 1.5.9 docs & runtime test | Default ONNX MiniLM embedding function works locally; cosine space via `{"hnsw:space": "cosine"}`; distance metric is cosine distance where lower is closer | Validated zero-cost local embedding architecture without PyTorch dependency | 2026-10-18 |

**Planning-stage claims to re-verify yourself** (they were observed during planning but must be confirmed by your own run; tick when done):

- [x] The primary PDF has 11 pages and the performance-review text on page 4 says reviews are conducted annually (PRD F-1, F-3) — confirmed by RAG-001/RAG-003 and by opening the PDF.
- [x] No PTO/vacation/benefits text exists in the handbook (PRD F-5) — confirmed by RAG-005 and keyword search.
- [x] The PDF has no printed page numbers that differ from the PDF index (V-13, D-14).
- [x] The planned chunking yields about 26 chunks (not a hard requirement) — confirmed: exactly 26 chunks produced.
- [x] The `langgraph-checkpoint-sqlite` package and its async saver behave as described (V-03) — confirmed: `AsyncSqliteSaver.from_conn_string` manages `aiosqlite` connection pool in lifespan; tables and WAL journal verified; state restores after process restart.

---

## 7. Lessons learned

Short, specific, dated. Prefer lessons that changed how you work (e.g., "write the routing test first", "print state before and after the failing turn").

| # | Date | Phase | Lesson | Where it changed my process |
|---|---|---|---|---|
| L-01 | `____` | `____` | `____` | `____` |

---

## 8. Near-misses caught in review (use if §4 has no real incidents, or in addition)

Cases where you read AI-generated code and caught a problem **before** it caused a failure. These count only if real.

| # | Date | Phase | What the AI generated | What I noticed | How I confirmed it was a problem | Fix |
|---|---|---|---|---|---|---|
| NM-01 | `____` | `____` | `____` | `____` | `____` | `____` |

---

## 9. README condensation checklist (Phase 8)

The README's *AI Engineering Log* section must contain:

- [ ] List of all AI tools/models used (from §1).
- [ ] 2–5 of the most instructive real incidents, each with symptom → evidence → root cause → fix → verification (from §4), or an honest statement plus near-misses (from §8).
- [ ] A link to this full log.
- [ ] No claim that is not backed by an entry above.