# agentos_core/app/models/gateway.py

from pydantic import BaseModel, Field, ConfigDict  
from typing import List, Optional, Dict, Any, Literal, Union

# Reutilizar PyObjectId  
from app.modules.people.models import PyObjectId

# --- Schemas de Request para /gateway/process ---  
class NaturalLanguagePayload(BaseModel):  
    text: str = Field(..., min_length=1)

class StructuredPayload(BaseModel):  
    intent: Optional[str] = None # Intenção explícita (opcional)  
    parameters: Dict[str, Any] = Field(default={}) # Parâmetros estruturados

class RequestContext(BaseModel):  
    explain: bool = Field(default=False, description="Se True, solicita log de explicação do raciocínio.")  
    # Adicionar outros contextos da UI se necessário  
    current_view: Optional[str] = None  
    # session_id para histórico de chat (diferente de conversation_id)  
    session_id: Optional[str] = None

class GatewayRequest(BaseModel):  
    # conversation_id é para o histórico do Advisor  
    conversation_id: Optional[str] = Field(None, description="ID da conversa Advisor existente para continuar o histórico.")  
    user_id: str # <<< OBRIGATÓRIO: ID do usuário (string ObjectId) - será validado contra token  
    request_type: Literal["natural_language", "structured"]  
    # Usar 'Union' com discriminador explícito (embora Pydantic v2 infira bem)  
    payload: Union[NaturalLanguagePayload, StructuredPayload] # type: ignore  
    context: Optional[RequestContext] = None

    # Validador para garantir que user_id é um ObjectId válido  
    @field_validator('user_id')  
    @classmethod  
    def validate_user_id(cls, v):  
        if not ObjectId.is_valid(v):  
            raise ValueError("Invalid user_id format (must be ObjectId string)")  
        return v

    model_config = ConfigDict(  
        json_schema_extra={  
           "example_nl": {  
                "user_id": "662f1a9fdd8a4b5e6f7d5678",  
                "request_type": "natural_language",  
                "payload": {"text": "Qual o status da entrega DLV-2025-00123?"},  
                "context": {"explain": True}  
           },  
            "example_structured": {  
                "conversation_id": "663a5b12f1a4e7d8c9b0f1e2",  
                "user_id": "662f1a9fdd8a4b5e6f7d5678",  
                "request_type": "structured",  
                "payload": {"intent": "get_order_details", "parameters": {"order_ref": "ORD-2025-00456"}}  
           }  
        }  
    )

# --- Schemas de Response de /gateway/process ---  
class FollowUpActionPayload(BaseModel):  
    intent: str  
    parameters: Dict[str, Any] = {}

class FollowUpAction(BaseModel):  
    label: str  
    action: FollowUpActionPayload

class NaturalLanguageResponsePayloadAPI(BaseModel):  
    text: str

class StructuredResponsePayloadAPI(BaseModel):  
    # O tipo de 'data' pode variar muito, usar 'Any' é flexível para a API  
    data: Any = Field(..., description="Resultado estruturado da ferramenta/serviço executado.")  
    # Opcional: Adicionar metadados sobre a origem dos dados  
    # data_source: Optional[str] = None

class ErrorResponsePayloadAPI(BaseModel):  
    error_code: str # Usar string para flexibilidade, mas documentar códigos comuns  
    message: str  
    details: Optional[Any] = None # Pode ser dict, string, etc.

class GatewayResponse(BaseModel):  
    # conversation_id retornado para o frontend saber qual conversa usar/atualizar  
    conversation_id: Optional[str] = Field(None, description="ID da conversa Advisor usada ou criada.")  
    response_type: Literal[  
        "natural_language_text", "structured_data", "error_message", "clarification_needed" # Adicionar tipo para pedir esclarecimento?  
    ]  
    # Usar Union para o payload  
    payload: Union[  
        NaturalLanguageResponsePayloadAPI,  
        StructuredResponsePayloadAPI,  
        ErrorResponsePayloadAPI,  
        None # Payload pode ser nulo para certos tipos? (ex: clarification_needed)  
    ] # type: ignore

    follow_up_actions: Optional[List[FollowUpAction]] = None  
    suggested_emotion: Optional[str] = None # Joia #3  
    explanation: Optional[List[str]] = None # Joia #4 (Modo Explicador)

    model_config = ConfigDict(  
         json_schema_extra={  
           "example_nl_response": {  
                "conversation_id": "663a5b12f1a4e7d8c9b0f1e2",  
                "response_type": "natural_language_text",  
                "payload": {"text": "Seu pedido ORD-123 está atualmente 'Em processamento'."},  
                "follow_up_actions": [{"label": "Ver detalhes", "action": {"intent": "get_order_details", "parameters": {"order_ref": "ORD-123"}}}],  
                "suggested_emotion": "informative"  
           },  
           "example_structured_response": {  
                "conversation_id": "663a5b12f1a4e7d8c9b0f1e2",  
                "response_type": "structured_data",  
                "payload": {"data": [{"id": "prod_abc", "name": "Produto A", "price": "99.90"}, {"id": "prod_def", "name": "Produto B", "price": "149.00"}]},  
                "follow_up_actions": [],  
                "suggested_emotion": "neutral_informative"  
           }  
         }  
    )

# --- Modelos internos para LLM (usados pelo GatewayService) ---  
# Estes não são expostos via API

class LLMToolCallFunction(BaseModel):  
    name: str  
    arguments: str # LLM retorna como string JSON

class LLMToolCall(BaseModel):  
    id: str # ID da chamada, fornecido pelo LLM  
    type: Literal["function"] = "function"  
    function: LLMToolCallFunction

class LLMResponseMessage(BaseModel):  
    role: Literal["assistant"]  
    content: Optional[str] = None # Resposta textual (se não for tool call)  
    tool_calls: Optional[List[LLMToolCall]] = None

class LLMError(BaseModel):  
    code: Optional[str] = None  
    message: str  
    type: Optional[str] = None  
    param: Optional[str] = None

class LLMResponseChoice(BaseModel):  
     index: int  
     message: LLMResponseMessage  
     finish_reason: Optional[str] = None # stop, length, tool_calls, content_filter, function_call (obsoleto)

class LLMResponse(BaseModel):  
    """Estrutura simplificada/validada da resposta da API OpenAI ChatCompletion."""  
    id: str  
    object: str  
    created: int  
    model: str  
    choices: List[LLMResponseChoice] = [] # Garantir que seja lista  
    usage: Optional[Dict[str, int]] = None  
    error: Optional[LLMError] = None # Capturar erro explícito da API

    # Adicionar validação para garantir que choices não esteja vazio se não houver erro  
    # @validator('choices', always=True)  
    # def check_choices_or_error(cls, v, values):  
    #     if not v and not values.get('error'):  
    #         # raise ValueError("LLM response must have choices or an error.")  
    #         logger.warning("LLM response received with no choices and no explicit error.")  
    #         # Adicionar um choice dummy para evitar quebras? Ou deixar o Gateway lidar?  
    #     return v

# Importar ObjectId para validação  
from bson import ObjectId
