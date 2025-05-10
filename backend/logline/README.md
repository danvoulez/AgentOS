# LogLine V2: Pragmatic Core

This backend implements the LogLine V2 philosophy, prioritizing immediate consistency and reliability while maintaining the core principles of immutable logging and auditability.

**Core Concepts:**

*   **Log First:** All significant actions generate an immutable `LogEvent` first.
*   **Synchronous State:** Core application state (`current_state_*` collections) is updated synchronously immediately after logging an event.
*   **Fast Reads:** Queries read from the `current_state` for speed and consistency.
*   **Auditability:** The full, immutable history is available via the `/timeline` endpoint reading from the `logs` collection.
*   **Dual Input:** Accepts natural language via `/gateway/process` (LLM) and structured commands via `/actions/*`.
*   **Real-time:** Broadcasts confirmed events via WebSockets.

**Stack:**

*   FastAPI
*   Pydantic V2
*   Motor (Async MongoDB)
*   Loguru
*   OpenAI (or other LLM)
*   OPA (via HTTP call or library)
*   Poetry

**(Setup and Run instructions similar to previous versions, referencing the new structure and compose file)**