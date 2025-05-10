# 🧪 Testes Obrigatórios — LogLine V2 & NewFlipApp

## 1. WebSocket: Recebimento de `new_log_event_v2` após cada operação

- **Backend (pytest):**
  - Mantenha conexão WS durante cada teste de ação.
  - Após operação (`/actions/*` ou `/gateway/process`), aguarde mensagem WS.
  - Assert:
    - `"type": "new_log_event_v2"`
    - `payload.id`, `payload.type`, `payload.author` e `payload.data` corretos.
- **Frontend (Manual/E2E):**
  - Realize operação na UI.
  - Confirme recebimento de mensagem no WebSocketContext e atualização da UI.

---

## 2. Testes de Permissão de Acionamento via OPA

- **Backend (pytest):**
  - Seed log original.
  - Teste com usuário permitido: espera status 200 e criação de log_acionado.
  - Teste com usuário negado: espera status 403 e mensagem OPA.
- **Exemplo:**
  ```python
  async def test_acionar_log_permission_denied_for_customer(...):
      # ...setup...
      response = await customer_client.post(.../actions/acionar_log, ...)
      assert response.status_code == 403
  ```

---

## 3. E2E: Usuário → Solicitação Ambígua → Formulário → Log → Estado → Timeline

- **Backend (pytest, mock LLM):**
  - 1. POST `/gateway/process` com frase ambígua → espera `form_request`.
  - 2. POST `/gateway/process` com `context.form_submission` → espera `operational_action_proposed` e criação do LogEvent correto.
  - 3. Verifique LogEvent, CurrentState e mensagem WS.
- **Frontend (Manual/E2E):**
  - Simule o fluxo completo na UI, validando respostas e atualização da timeline.

---

## 4. Renderização Adaptativa de Dados

- **Backend:** Crie endpoint `/admin/test_render_data` para enviar dados arbitrários para teste visual.
- **Frontend:** 
  - Envie variações de dados (tabela, key-value, cards, fallback).
  - Verifique o SmartBlock/StructuredDataRenderer renderizando corretamente e aplicando hints do display_meta.

---

## Observações

- Sempre assegure que:
  - O ciclo log → consequence → acionamento → execução está fechado.
  - Toda ação operacional e acionamento relevante dispara o evento WS correto.
  - Permissões OPA são realmente testadas e respeitadas.
  - UI reage a eventos do backend, sem necessidade de refresh manual.

---

Com a passagem desses testes, o LogLine V2 estará pronto para produção com confiança institucional.
