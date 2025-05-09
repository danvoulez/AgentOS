# agentos_core/app/models/tasks.py

from pydantic import BaseModel, Field, ConfigDict, field_validator  
from typing import List, Optional, Literal, Dict, Any  
from datetime import datetime, date

from app.modules.people.models import PyObjectId # Reutilizar

# Status e Prioridades (consistente com modelo interno)  
TASK_STATUSES = Literal["pending", "in_progress", "completed", "cancelled", "blocked"]  
TASK_PRIORITIES = Literal["low", "medium", "high", "urgent"]

# --- Schemas para API ---

class TaskAPI(BaseModel):  
    """Schema para retornar dados de tarefa via API."""  
    id: PyObjectId  
    title: str  
    description: Optional[str] = None  
    status: TASK_STATUSES  
    priority: TASK_PRIORITIES  
    assigned_to: Optional[PyObjectId] = None  
    assigned_to_details: Optional[Dict] = Field(None, description="Detalhes do usuário responsável (enriquecido).")  
    due_date: Optional[date] = None # Retornar como data  
    created_by: PyObjectId  
    created_by_details: Optional[Dict] = Field(None, description="Detalhes do criador (enriquecido).")  
    created_at: datetime  
    updated_at: datetime  
    completed_at: Optional[datetime] = None  
    related_entity_type: Optional[str] = None  
    related_entity_id: Optional[str] = None  
    source_context: Optional[str] = None  
    tags: List[str] = []

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={  
            datetime: lambda v: v.isoformat() if v else None,  
            date: lambda v: v.isoformat() if v else None # Codificar data como YYYY-MM-DD  
        }  
    )

class TaskCreateAPI(BaseModel):  
    """Payload para criar uma nova tarefa via API."""  
    title: str = Field(..., min_length=3)  
    description: Optional[str] = None  
    priority: TASK_PRIORITIES = "medium"  
    # Receber IDs como string na API  
    assigned_to_id: Optional[str] = Field(None, description="ID do usuário responsável (opcional).")  
    due_date_str: Optional[str] = Field(None, description="Data limite (YYYY-MM-DD) (opcional).")  
    related_entity_type: Optional[str] = None  
    related_entity_id: Optional[str] = None  
    source_context: Optional[str] = Field(None, description="Contexto de origem (ex: 'Manual', 'Gateway:...')")  
    tags: Optional[List[str]] = None

    @field_validator('assigned_to_id')  
    @classmethod  
    def check_assignee_id(cls, v):  
        if v is not None and not ObjectId.is_valid(v):  
            raise ValueError("Invalid assigned_to_id format.")  
        return v

    @field_validator('due_date_str')  
    @classmethod  
    def check_due_date(cls, v):  
        if v is not None:  
            try:  
                datetime.strptime(v, '%Y-%m-%d')  
            except ValueError:  
                raise ValueError("Invalid due_date_str format. Use YYYY-MM-DD.")  
        return v

    model_config = ConfigDict(json_schema_extra={  
        "example": {  
            "title": "Follow up with Customer Z",  
            "description": "Call customer Z regarding quote sent last week.",  
            "priority": "high",  
            "assigned_to_id": "662f1a9fdd8a4b5e6f7d5678",  
            "due_date_str": "2025-05-15",  
            "tags": ["follow-up", "customer-z"]  
        }  
    })

class TaskUpdateAPI(BaseModel):  
    """Payload para atualizar uma tarefa existente via API."""  
    title: Optional[str] = Field(None, min_length=3)  
    description: Optional[str] = None  
    status: Optional[TASK_STATUSES] = None  
    priority: Optional[TASK_PRIORITIES] = None  
    # Usar None explicitamente para desatribuir  
    assigned_to_id: Optional[str | None] = Field(None, description="ID do novo responsável ou None para desatribuir.")  
    due_date_str: Optional[str | None] = Field(None, description="Nova data limite (YYYY-MM-DD) ou None para remover.")  
    related_entity_type: Optional[str] = None  
    related_entity_id: Optional[str] = None  
    source_context: Optional[str] = None  
    tags: Optional[List[str]] = None

    # Validadores similares aos do CreateAPI para IDs e Datas  
    @field_validator('assigned_to_id')  
    @classmethod  
    def check_update_assignee_id(cls, v):  
        if v is not None and not ObjectId.is_valid(v):  
             raise ValueError("Invalid assigned_to_id format.")  
        return v

    @field_validator('due_date_str')  
    @classmethod  
    def check_update_due_date(cls, v):  
        if v is not None:  
            try: datetime.strptime(v, '%Y-%m-%d')  
            except ValueError: raise ValueError("Invalid due_date_str format. Use YYYY-MM-DD.")  
        return v

# Importar ObjectId para validação  
from bson import ObjectId
