# LogEvent.data Contract for Operational Event Types

This document defines the expected Pydantic model for the `data` field of a `LogEvent`
for each supported operational `LogEvent.type`. This contract must be followed by:

- **LLMService** (when generating `entities` for `operational_action_proposed`)
- **/gateway/process** (when building a LogEvent from LLM `entities`)
- **/actions/* endpoints** (when constructing `event_data_for_log` from payload)
- **StateUpdaterService** (when parsing `LogEvent.data` for state updates)
- **Frontend (NewFlipApp)** (for building forms and previewing/parsing LogEvent data)

---

## Type: `registrar_venda`
**Pydantic Model:** `app.models.RegistrarVendaData`
```json
{
  "order_id": "ord_abc123",
  "customer_id": "user_001",
  "items": [
    {
      "product_id": "prod_001",
      "quantity": 2,
      "name": "Produto Exemplo",
      "price_per_unit_str": "19.90"
    }
  ],
  "total_amount_str": "39.80",
  "channel": "whatsapp_validated",
  "status": "confirmed",
  "_raw_user_input_payload": { "original_whatsapp_message": "Quero 2 Produto Exemplo" }
}
```
**Required Fields:** `order_id`, `customer_id`, `items` (list of `ItemVendaData`), `total_amount_str`, `channel`, `status`

---

## Type: `relato_quebra`
**Pydantic Model:** `app.models.RelatoQuebraData`
```json
{
  "product_id": "prod_001",
  "quantity": 1,
  "reason": "Quebrou durante o transporte",
  "reported_by": "user_123",
  "notes": "Cliente enviou foto da quebra"
}
```
**Required Fields:** `product_id`, `quantity`, `reason`, `reported_by`

---

## Type: `entrada_estoque`
**Pydantic Model:** `app.models.EntradaEstoqueData`
```json
{
  "product_id": "prod_001",
  "quantity": 10,
  "received_by": "user_123",
  "notes": "Reposição mensal"
}
```
**Required Fields:** `product_id`, `quantity`, `received_by`

---

## Type: `despacho_created`
**Pydantic Model:** `app.models.DespachoCreatedData`
```json
{
  "despacho_id": "dsp_123abc",
  "triggering_log_event_id": "evt_wa_001",
  "despacho_type": "validar_prelog_whatsapp",
  "assigned_to": "role:atendente_whatsapp_n1",
  "due_at_iso": "2025-12-31T17:00:00Z",
  "context_data": {
    "prelog_id": "evt_wa_001",
    "sender": "whatsapp:+5511999998888",
    "message_snippet": "Preciso de ajuda"
  },
  "notes": "Validar manualmente a mensagem recebida."
}
```
**Required Fields:** `despacho_id`, `triggering_log_event_id`, `despacho_type`, `assigned_to`, `due_at_iso`, `context_data`

---

## Type: `despacho_resolved`
**Pydantic Model:** `app.models.DespachoResolvedData`
```json
{
  "despacho_id": "dsp_123abc",
  "resolution_type": "resolved_manual",
  "resolved_by": "user_123",
  "resolution_notes": "Despacho resolvido após validação."
}
```
**Required Fields:** `despacho_id`, `resolution_type`, `resolved_by`

---

## Type: `approve_prelog`
**Pydantic Model:** `app.models.ValidarPrelogData`
```json
{
  "target_prelog_id": "evt_wa_001",
  "validator_id": "admin@example.com",
  "validation_status": "approved",
  "validation_notes": "Tudo correto.",
  "corrected_operational_data": {
    "type_to_create": "registrar_venda",
    "data_for_state_updater": { /* see RegistrarVendaData above */ }
  },
  "resulting_operational_log_event_id": "evt_op_002"
}
```
**Required Fields:** `target_prelog_id`, `validator_id`, `validation_status`, `resulting_operational_log_event_id`

---

## Type: `reject_prelog`
**Pydantic Model:** `app.models.ValidarPrelogData`
```json
{
  "target_prelog_id": "evt_wa_001",
  "validator_id": "admin@example.com",
  "validation_status": "rejected",
  "validation_notes": "Mensagem irrelevante.",
  "resulting_operational_log_event_id": null
}
```
**Required Fields:** `target_prelog_id`, `validator_id`, `validation_status`

---

## Type: `whatsapp_mensagem_recebida`
**Pydantic Model:** `app.models.WhatsAppMensagemRecebidaData`
```json
{
  "prelog_id": "evt_wa_001",
  "sender_wa_id": "whatsapp:+5511999998888",
  "message_text": "Preciso de ajuda com meu pedido.",
  "initial_llm_interpretation": {
    "intent": "unknown_intent"
  }
}
```
**Required Fields:** `prelog_id`, `sender_wa_id`, `message_text`

---

**Note:**  
- All operational LogEvents must set `data` to the structure above for the appropriate `type`.
- These contracts are enforced by Pydantic validation throughout the system.
- If extending with new LogEvent types, update this document and the `*Data` models accordingly.

---