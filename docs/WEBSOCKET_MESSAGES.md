# LogLine V2: WebSocket Message Contract (v1.0)

This document outlines the structure of messages sent from the LogLine V2 backend server to connected NewFlipApp WebSocket clients.

## Connection & Authentication

- **Endpoint:** `/ws/updates`
- **Authentication:** Clients MUST connect by providing a valid JWT access token as a query parameter named `token`.
  Example: `wss://your_backend_domain/ws/updates?token=<JWT_ACCESS_TOKEN>`
- Server will close connections with invalid or missing tokens with code `1008 (Policy Violation)`.

## General Message Structure

All server-sent messages will be JSON objects with at least a `type` field identifying the nature of the message.

```json
{
  "type": "message_type_identifier_string",
  "payload": {
    // Structure of payload depends on the 'type'
  },
  "timestamp_utc": "ISO8601_timestamp_of_message_emission" // Recommended for all messages
}
```

## Standard Message Types

### 1. `new_log_event_v2` (Primary Message)

- **Description:** Sent whenever any new `LogEvent` is successfully recorded by `LogService` and its primary synchronous state updates (via `StateUpdaterService`) are completed. This is the most frequent and comprehensive message type. NewFlipApp should inspect the `payload.type` (LogEvent type) and `payload.data` to understand the nature of the change and update relevant UI sections.
- **Payload:** The full `LogEvent` Pydantic model, serialized to JSON (as per `LogEvent.model_dump(mode='json')`).
- **Example:**
    ```json
    {
      "type": "new_log_event_v2",
      "payload": {
        "id": "evt_c2f4b7a0...",
        "timestamp": "2024-05-17T10:30:05.123Z",
        "type": "registrar_venda",
        "author": "user_db_id_of_staff_member",
        "witness": "action:/api/v1/actions/registrar_venda",
        "channel": "fusion_structured_action",
        "origin": "SalesTerminalForm_A",
        "data": {
          "order_id": "ord_a1b2c3d4",
          "customer_id": "user_db_id_of_customer",
          "items": [
            {"product_id": "prod_xyz", "quantity": 2, "name": "Produto XYZ", "price_per_unit_str": "25.50"}
          ],
          "total_amount_str": "51.00",
          "channel": "fusion_structured_action",
          "status": "confirmed"
        },
        "consequence": {"order_id": "ord_a1b2c3d4", "status_set": "confirmed"},
        "meta": {"trace_id": "req_123...", "conversation_id": "conv_789..."}
      },
      "timestamp_utc": "2024-05-17T10:30:05.500Z"
    }
    ```

### 2. `fusion_hint`

- **Description:** Provides a suggestion, informational message, warning, or error to the user, potentially with a suggested action. Can be triggered by `LLMService` (via `LogEvent.consequence` processed by `LogService`) or by other system logic.
- **Payload Structure:**
    ```json
    {
      "hint_type": "info" | "warning" | "success" | "error" | "suggestion",
      "text": "User-friendly message for the hint panel or a toast notification.",
      "title": "Optional Hint Title",
      "action": {
        "label": "View Item" | "Create Reorder Task",
        "intent_to_trigger": "query_inventory_item" | "create_despacho",
        "parameters_for_intent": { "product_id": "prod_123" }
      },
      "auto_dismiss_ms": 5000,
      "icon_name": "Optional: icon identifier for NewFlipApp to use (e.g., 'bell', 'warning_triangle')"
    }
    ```
- **Example:**
    ```json
    {
      "type": "fusion_hint",
      "payload": {
        "hint_type": "warning",
        "title": "Low Stock Warning",
        "text": "Product 'Super Widget' (prod_sw001) stock is below threshold (Current: 3).",
        "action": {
          "label": "Reorder Now",
          "intent_to_trigger": "create_despacho",
          "parameters_for_intent": {
            "despacho_type": "reabastecer_estoque_urgente",
            "context_data": {"product_id": "prod_sw001", "current_stock": 3}
          }
        },
        "auto_dismiss_ms": null
      },
      "timestamp_utc": "2024-05-17T10:35:00.100Z"
    }
    ```

### 3. `despacho_status_updated` (Granular Update - Optional for V2 Core, but good to define)

- **Description:** Sent specifically when a `CurrentStateDespacho` is created or its status changes. This is more targeted than just sending the full `despacho_created` or `despacho_resolved` LogEvent again (though `new_log_event_v2` *will* also send those). This allows for efficient updates of a "Despacho List" view in NewFlipApp.
- **Payload:** The full `CurrentStateDespacho` Pydantic model, serialized to JSON.
- **Example:**
    ```json
    {
      "type": "despacho_status_updated",
      "payload": {
        "_id": "dsp_wa_val_evt_prelog_wa_abc",
        "triggering_log_event_id": "evt_prelog_wa_abc...",
        "despacho_type": "validar_prelog_whatsapp",
        "status": "assigned",
        "assigned_to": "user_atendente_id",
        "assigned_to_name": "Atendente João",
        "last_log_event_id": "evt_despacho_assigned_xyz",
        "last_updated_at": "2024-05-17T10:40:00.200Z"
      },
      "timestamp_utc": "2024-05-17T10:40:00.250Z"
    }
    ```

### 4. `prelog_status_updated` (Granular Update - Optional for V2 Core)

- **Description:** Sent when a `CurrentStatePreLog` status changes (e.g., from `pending_validation_whatsapp` to `approved` or `rejected`).
- **Payload:** The full `CurrentStatePreLog` Pydantic model, serialized.

### 5. `whatsapp_message_status_provider` (If integrating WhatsApp provider status callbacks)

- **Description:** Relays status updates received from the WhatsApp provider for an *outgoing* message (e.g., "sent", "delivered", "read", "failed").
- **Payload Structure:**
    ```json
    {
      "internal_message_log_id": "evt_enviar_whatsapp_solicitado_xyz",
      "provider_message_id": "wamid.XYZ...",
      "chat_id": "whatsapp:+15551234567",
      "status_from_provider": "sent" | "delivered" | "read" | "failed",
      "timestamp_from_provider": "ISO8601_UTC_timestamp_of_status_update",
      "error_details": {
        "code": 131051,
        "message": "Message failed to send because the user is out of coverage."
      }
    }
    ```

### 6. `server_keepalive_ping`
- **Description:** Sent by the server if no client message is received within a timeout period, to help keep the connection alive. NewFlipApp can ignore this or use it to detect server liveness.
- **Payload:** Simple text string `"server_keepalive_ping"`. (Note: `websockets.py` sends this as raw text. For consistency, it *could* be wrapped in the standard JSON structure: `{"type": "server_keepalive_ping", "payload": null, "timestamp_utc": "..."}`)

---

This `WEBSOCKET_MESSAGES.md` provides a clear contract. For V2 Pragmatic Core, **`new_log_event_v2` is the workhorse.** NewFlipApp will primarily listen for this, inspect `log_event.type`, and update its state/views accordingly. More granular messages like `despacho_status_updated` can be added as optimizations if re-rendering based on the full `LogEvent` becomes inefficient for specific views.