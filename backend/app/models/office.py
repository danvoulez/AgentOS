# agentos_core/app/models/office.py

from pydantic import BaseModel, Field, ConfigDict  
from typing import Any, Optional, Dict, List, Literal  
from datetime import datetime

# Reutilizar PyObjectId  
from app.modules.people.models import PyObjectId

# --- Schemas de Settings API ---

class SettingAPI(BaseModel):  
    """Schema para retornar uma configuração via API (valor pode ser ofuscado)."""  
    key: str = Field(..., description="Chave única da configuração.")  
    value: Any = Field(..., description="Valor da configuração (pode ser '*****' se for sensível).")  
    description: Optional[str] = None  
    is_sensitive: bool = Field(..., description="Indica se o valor original é sensível.")  
    updated_at: datetime

    model_config = ConfigDict(  
        from_attributes=True, # Para validar a partir do modelo DB  
        json_encoders={datetime: lambda v: v.isoformat()}  
    )

class SettingCreateAPI(BaseModel):  
    """Payload para criar uma nova configuração via API."""  
    key: str = Field(..., min_length=3, pattern=r"^[a-zA-Z0-9_.-]+$", description="Chave única (letras, números, _, ., -).")  
    value: Any = Field(..., description="Valor da configuração.")  
    description: Optional[str] = None  
    is_sensitive: bool = False

    model_config = ConfigDict(  
        json_schema_extra={  
            "example": {  
                "key": "feature_flag_new_dashboard",  
                "value": True,  
                "description": "Habilita o novo dashboard beta.",  
                "is_sensitive": False  
            }  
        }  
    )

class SettingUpdateAPI(BaseModel):  
    """Payload para atualizar uma configuração existente via API."""  
    # Key não pode ser atualizado via PATCH/PUT no ID  
    value: Optional[Any] = Field(None, description="Novo valor para a configuração.") # Usar None para não atualizar  
    description: Optional[str] = None  
    is_sensitive: Optional[bool] = None

    model_config = ConfigDict(  
        json_schema_extra={  
            "example": {  
                "value": False,  
                "description": "Desabilita o novo dashboard beta temporariamente."  
            }  
        }  
    )

# --- Schemas de Audit Log API ---

class AuditLogAPI(BaseModel):  
    """Schema para retornar uma entrada de log de auditoria via API."""  
    id: PyObjectId = Field(..., description="ID interno do log.")  
    timestamp: datetime  
    # Retornar user_id como string para API  
    user_id: Optional[str] = Field(None, description="ID do usuário que realizou a ação (se aplicável).")  
    user_email: Optional[str] = Field(None, description="Email do usuário (desnormalizado).")  
    action: str = Field(..., description="Ação realizada (ex: 'order_created').")  
    entity_type: Optional[str] = Field(None, description="Tipo da entidade afetada (ex: 'Order').")  
    entity_id: Optional[str] = Field(None, description="ID da entidade afetada.")  
    details: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais sobre a ação.")  
    ip_address: Optional[str] = None  
    status: Literal["success", "failure"]  
    error_message: Optional[str] = None

    model_config = ConfigDict(  
        from_attributes=True,  
        json_encoders={datetime: lambda v: v.isoformat()}  
    )
