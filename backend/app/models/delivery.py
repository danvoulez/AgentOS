# agentos_core/app/models/delivery.py

from pydantic import BaseModel, Field, field_validator, ConfigDict # Usar field_validator  
from typing import List, Optional, Dict, Any, Tuple  
from datetime import datetime

from app.modules.people.models import PyObjectId # Reutilizar

# Status (consistente com modelo interno)  
DELIVERY_STATUSES = ["pending", "assigned", "in_transit", "out_for_delivery", "delivered", "failed", "returned", "cancelled"]

# --- Schemas para API ---

class TrackingEventAPI(BaseModel):  
    """Evento de rastreamento para exibição na API."""  
    timestamp: datetime  
    status: str  
    location_note: Optional[str] = None  
    notes: Optional[str] = None  
    # Não expor geo_point na API por padrão?

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

class DeliveryAPI(BaseModel):  
    """Schema completo de entrega retornado pela API."""  
    id: PyObjectId = Field(..., description="ID interno da entrega")  
    delivery_ref: str = Field(..., description="Referência única da entrega (DLV-...).")  
    order_id: PyObjectId  
    customer_id: PyObjectId  
    delivery_address: Dict[str, Any] # Endereço de entrega  
    current_status: str  
    assigned_driver_id: Optional[PyObjectId] = None  
    # Detalhes do motorista (opcional, enriquecido)  
    driver_details: Optional[Dict[str, Any]] = Field(None, description="Detalhes do motorista atribuído (enriquecido).")  
    tracking_history: List[TrackingEventAPI] = []  
    estimated_delivery_date: Optional[datetime] = None  
    actual_delivery_date: Optional[datetime] = None  
    shipping_notes: Optional[str] = None # Instruções do pedido  
    delivery_notes: Optional[str] = None # Notas adicionais da entrega  
    created_at: datetime  
    updated_at: datetime

    model_config = ConfigDict(  
        populate_by_name = True,  
        from_attributes=True,  
        json_encoders={datetime: lambda v: v.isoformat() if v else None}  
    )

class AssignDriverPayloadAPI(BaseModel):  
    """Payload para atribuir um motorista via API."""  
    driver_id: str = Field(..., description="ID do usuário (motorista) a ser atribuído.")

    @field_validator('driver_id')  
    @classmethod  
    def check_driver_id(cls, value):  
        if not ObjectId.is_valid(value):  
            raise ValueError("Invalid driver_id format (must be ObjectId).")  
        return value

    model_config = ConfigDict(json_schema_extra={"example": {"driver_id": "662f1a9fdd8a4b5e6f7d5678"}})

class UpdateStatusPayloadAPI(BaseModel):  
    """Payload para atualizar o status da entrega via API."""  
    status: str = Field(..., description=f"Novo status da entrega. Válidos: {DELIVERY_STATUSES}")  
    location_note: Optional[str] = Field(None, description="Localização atual ou nota sobre o status.")  
    notes: Optional[str] = Field(None, description="Notas adicionais (ex: motivo da falha).")

    @field_validator('status')  
    @classmethod  
    def check_status_valid(cls, v: str):  
        if v not in DELIVERY_STATUSES:  
            raise ValueError(f"Invalid delivery status. Must be one of: {DELIVERY_STATUSES}")  
        return v

    model_config = ConfigDict(json_schema_extra={"example": {"status": "in_transit", "location_note": "Saiu do centro de distribuição."}})

class AddTrackingEventPayloadAPI(BaseModel):  
    """Payload para adicionar um evento de tracking manual via API."""  
    status: str = Field(..., description="Descrição do status do evento.")  
    location_note: Optional[str] = Field(None, description="Localização onde o evento ocorreu.")  
    notes: Optional[str] = Field(None, description="Notas adicionais sobre o evento.")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "Tentativa de Entrega", "location_note": "Endereço do Cliente", "notes": "Cliente ausente."}})

# Importar ObjectId para validação  
from bson import ObjectId
