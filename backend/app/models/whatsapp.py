# agentos_core/app/models/whatsapp.py

from pydantic import BaseModel, Field, field_validator, ConfigDict  
from typing import List, Optional, Dict, Any, Union  
from datetime import datetime

# Reutilizar PyObjectId  
from app.modules.people.models import PyObjectId

# --- Modelos para Webhook Meta (sem mudanças, apenas referência interna) ---  
class WhatsAppWebhookText(BaseModel): body: str  
class WhatsAppWebhookMedia(BaseModel): id: str; mime_type: Optional[str] = None; sha256: Optional[str] = None; caption: Optional[str] = None; filename: Optional[str] = None  
class WhatsAppWebhookLocation(BaseModel): latitude: float; longitude: float; name: Optional[str] = None; address: Optional[str] = None  
class WhatsAppWebhookContactProfile(BaseModel): name: str  
class WhatsAppWebhookContact(BaseModel): profile: WhatsAppWebhookContactProfile; wa_id: str  
class WhatsAppWebhookMessageContext(BaseModel): from_number: Optional[str] = Field(None, alias="from"); id: Optional[str] = None  
class WhatsAppWebhookMessage(BaseModel): id: str; from_number: str = Field(..., alias="from"); timestamp: str; type: str; text: Optional[WhatsAppWebhookText] = None; image: Optional[WhatsAppWebhookMedia] = None; audio: Optional[WhatsAppWebhookMedia] = None; document: Optional[WhatsAppWebhookMedia] = None; location: Optional[WhatsAppWebhookLocation] = None; contacts: Optional[List[Dict]] = None; sticker: Optional[WhatsAppWebhookMedia] = None; reaction: Optional[Dict] = None; context: Optional[WhatsAppWebhookMessageContext] = None; model_config = ConfigDict(populate_by_name=True)  
class WhatsAppWebhookStatus(BaseModel): id: str; recipient_id: str; status: str; timestamp: str; conversation: Optional[Dict] = None; pricing: Optional[Dict] = None; errors: Optional[List[Dict]] = None  
class WhatsAppWebhookValue(BaseModel): messaging_product: str; metadata: Dict[str, Any]; contacts: Optional[List[WhatsAppWebhookContact]] = None; messages: Optional[List[WhatsAppWebhookMessage]] = None; statuses: Optional[List[WhatsAppWebhookStatus]] = None  
class WhatsAppWebhookChange(BaseModel): value: WhatsAppWebhookValue; field: str  
class WhatsAppWebhookEntry(BaseModel): id: str; changes: List[WhatsAppWebhookChange]  
class WhatsAppWebhookPayload(BaseModel): object: str; entry: List[WhatsAppWebhookEntry]

# --- Modelos para API Endpoints ---  
class SendMessagePayloadAPI(BaseModel): # Renomeado de SendMessagePayload  
    """Payload para enviar mensagem via API /whatsapp/send."""  
    recipient_wa_id: str = Field(..., description="Recipient's WA ID (número SEM o '+').", pattern=r"^d+$")  
    content: str = Field(..., min_length=1, description="Conteúdo da mensagem de texto.")  
    # type é fixo como 'text' neste endpoint por enquanto  
    # type: str = Field(default="text")

    model_config = ConfigDict(json_schema_extra={"example": {"recipient_wa_id": "5511999998888", "content": "Olá! Seu pedido foi atualizado."}})

class SendMessageResponseAPI(BaseModel): # Renomeado de SendMessageResponse  
    """Resposta da API /whatsapp/send."""  
    status: str # "queued" ou "failed" (indica se foi enfileirado com sucesso)  
    internal_message_id: Optional[str] = Field(None, description="ID interno da mensagem criada no nosso DB.")  
    details: Optional[str] = None # Mensagem de erro se falhar ao enfileirar

class ChatModePayloadAPI(BaseModel): # Renomeado de ChatModePayload  
    """Payload para definir modo do chat via API."""  
    mode: Literal["human", "agent"] # Usar Literal para validação

    @field_validator('mode') # Manter validador explícito  
    @classmethod  
    def mode_must_be_valid(cls, v: str):  
        if v not in ['human', 'agent']: raise ValueError("Mode must be 'human' or 'agent'"); return v

class ChatModeResponseAPI(BaseModel): # Renomeado de ChatModeResponse  
    """Resposta da API de mudança de modo."""  
    chat_id: str  
    new_mode: str  
    status: str # "updated" ou "no_change" ou "not_found"

# --- Modelos para Retorno de Dados API ---  
class WhatsAppMessageAPI(BaseModel):  
    """Schema para retornar uma mensagem WA via API."""  
    id: str = Field(..., alias="_id", description="ID da mensagem (WAMI ou ID interno).")  
    chat_id: str  
    sender_id: str # user wa_id, agent, auto_responder, employee:username  
    recipient_id: str | None = None # your number_id ou user wa_id  
    content: str  
    type: str  
    timestamp: datetime # Timestamp original da Meta ou de criação interna  
    status: Optional[str] = None # pending_queue, pending_send, sent, delivered, read, failed_send, received, agent_error, failed_system  
    status_timestamp: Optional[datetime] = None # Timestamp da última atualização de status  
    # Incluir transcrição se for áudio  
    transcription: Optional[str] = Field(None, description="Transcrição se for mensagem de áudio.")  
    # Incluir WAMI oficial se diferente do _id  
    official_wami: Optional[str] = Field(None, description="WAMI oficial retornado pela Meta, se diferente do ID interno.")  
    # Incluir metadados relevantes?  
    metadata: Optional[Dict[str, Any]] = Field(None, exclude=True) # Excluir por padrão? Ou selecionar campos?  
    created_at: datetime # Quando foi salvo no nosso DB

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={datetime: lambda v: v.isoformat() if v else None}  
    )

class WhatsAppChatAPI(BaseModel):  
    """Schema para retornar um chat WA via API."""  
    id: str = Field(..., alias="_id", description="ID do Chat (WA ID do contato).")  
    contact_id: str # Redundante com ID, mas pode manter por clareza  
    contact_name: Optional[str] = None  
    mode: Literal["human", "agent"]  
    status: Literal["open", "closed", "archived"] # Adicionar mais status se necessário  
    last_message_ts: Optional[datetime] = None  
    last_message_preview: Optional[str] = Field(None, description="Preview da última mensagem (calculado).") # Adicionar preview  
    unread_count: int = 0  
    last_interaction_at: Optional[datetime] = None # Última vez que *nós* interagimos ou recebemos

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={datetime: lambda v: v.isoformat() if v else None}  
    )

# Importar Literal para tipos  
from typing import Literal
