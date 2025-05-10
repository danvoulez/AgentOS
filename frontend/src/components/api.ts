// ... (outros tipos existentes)

export type ACIONAMENTO_TYPE_LITERAL =
  | "confirmar_fato"
  | "negar_fato"
  | "acionar_testemunha"
  | "propor_ajuste"
  | "denunciar_ma_fe"
  | "solicitar_consequencia";

export interface AcionarLogEventActionAPIPayload {
  target_log_id: string;
  acionamento_type: ACIONAMENTO_TYPE_LITERAL;
  motivo?: string | null;
  dados_adicionais?: Record<string, any> | null;
  testemunha_acionada_id?: string | null;
}

export interface LogAcionadoData {
  target_log_id: string;
  acionamento_type: ACIONAMENTO_TYPE_LITERAL;
  motivo?: string | null;
  dados_adicionais?: Record<string, any> | null;
  testemunha_acionada_id?: string | null;
  _raw_user_input_payload?: Record<string, any> | null;
  _llm_full_interpretation?: Record<string, any> | null;
}

export interface LogAcionamentoInfo {
  log_acionado_event_id: string;
  acionamento_type: ACIONAMENTO_TYPE_LITERAL;
  author_acionamento: string;
  timestamp_acionamento: string;
  motivo?: string | null;
  status_resolucao_acionamento?: string;
}

export interface CurrentStateOrderStatus {
  // ... outros campos ...
  acionamentos?: LogAcionamentoInfo[];
  meta?: {
    last_acionamento_status?: Record<string, string>;
    has_pending_acionamentos?: boolean;
  };
}