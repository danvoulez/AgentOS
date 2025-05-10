from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Acionamento Institucional ---

ACIONAMENTO_INSTITUCIONAL_TYPE_LITERAL = Literal[
    "confirmar_veracidade",
    "contestar_fato",
    "denunciar_conduta",
    "solicitar_revisao_formal",
    "registrar_ciencia"
]

class AcionarLogInstitucionalActionAPIPayload(BaseModel):
    target_log_id: str = Field(..., description="ID do LogEvent original sendo acionado.")
    acionamento_type: ACIONAMENTO_INSTITUCIONAL_TYPE_LITERAL
    motivo_detalhado: str = Field(..., min_length=10, max_length=2000, description="Descrição detalhada do motivo do acionamento.")
    evidencias_anexas: Optional[List[Dict[str, str]]] = Field(None, description="Lista de links ou referências a evidências.")

class LogAcionadoInstitucionalmenteData(BaseModel):
    target_log_id: str
    acionamento_type: ACIONAMENTO_INSTITUCIONAL_TYPE_LITERAL
    motivo_detalhado: str
    evidencias_anexas: Optional[List[Dict[str, str]]] = None
    _raw_user_input_payload: Optional[Dict[str, Any]] = Field(None, exclude=True)
    _llm_full_interpretation: Optional[Dict[str, Any]] = Field(None, exclude=True)

class LitigioInstitucionalInfo(BaseModel):
    log_acionamento_event_id: str
    acionamento_type: ACIONAMENTO_INSTITUCIONAL_TYPE_LITERAL
    author_acionamento: str
    timestamp_acionamento: datetime
    motivo: str
    status_litigio: Literal["aberto", "em_analise", "resolvido_favoravel", "resolvido_desfavoravel", "encerrado"] = "aberto"
    resolucao_log_event_id: Optional[str] = None
    resolucao_timestamp: Optional[datetime] = None
    resolucao_detalhes: Optional[str] = None

# Exemplo de uso em CurrentState*:
# litigios_institucionais: List[LitigioInstitucionalInfo] = Field(default_factory=list)
# meta: Dict[str, Any] = Field(default_factory=dict)