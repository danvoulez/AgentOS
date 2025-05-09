# agentos_core/app/models/people.py

from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator # Usar field_validator  
from typing import List, Optional, Dict, Any # Adicionar Dict, Any  
from datetime import datetime  
from bson import ObjectId # Importar ObjectId para validação interna

# Helper PyObjectId (se não for importado globalmente)  
# class PyObjectId(str): ... (definição completa)  
# Ou importar de um local centralizado, ex: app.models.api_common? Melhor aqui ou no Pydantic interno.  
# Por simplicidade, assumir que está definido ou importar de outro módulo (ex: agreements)  
from .agreements import PyObjectId # Exemplo de importação

# --- Schemas de Perfil ---  
class UserProfileAPI(BaseModel):  
    """Schema do perfil do usuário para respostas da API."""  
    first_name: Optional[str] = None  
    last_name: Optional[str] = None  
    phone: Optional[str] = None  
    # Adicionar outros campos de perfil conforme necessário (ex: avatar_url)

class UserProfileUpdateAPI(BaseModel):  
    """Payload para atualizar o perfil do usuário."""  
    first_name: Optional[str] = Field(None, min_length=1)  
    last_name: Optional[str] = Field(None, min_length=1)  
    phone: Optional[str] = None # Adicionar validação de formato de telefone se necessário

# --- Schemas de Usuário ---  
class UserAPI(BaseModel):  
    """Schema principal do usuário para respostas da API (dados públicos/semi-públicos)."""  
    id: PyObjectId = Field(..., description="ID único do usuário.")  
    email: EmailStr  
    profile: UserProfileAPI  
    roles: List[str] = []  
    is_active: bool  
    created_at: datetime  
    updated_at: datetime  
    # Opcional: Adicionar last_login, etc.  
    # Opcional: Adicionar tags RFID se forem expostas  
    rfid_tags: Optional[List[str]] = Field(None, description="Tags RFID associadas ao usuário (se houver).")

    model_config = ConfigDict(  
        from_attributes=True, # Para validar a partir do UserInDB  
        populate_by_name=True, # Se UserInDB usa _id  
        json_encoders={datetime: lambda v: v.isoformat()},  
        json_schema_extra={  
            "example": {  
                "id": "662f1a9fdd8a4b5e6f7d5678",  
                "email": "cliente@email.com",  
                "profile": {"first_name": "Joana", "last_name": "Silva", "phone": "+351912345678"},  
                "roles": ["customer", "vip"],  
                "is_active": True,  
                "created_at": "2024-04-26T10:00:00Z",  
                "updated_at": "2024-04-26T11:30:00Z",  
                "rfid_tags": ["E28011700000020F1234ABCD"]  
            }  
        }  
    )

class UserCreateAPI(BaseModel):  
    """Payload para criar um novo usuário via API (ex: registro)."""  
    email: EmailStr  
    password: str = Field(..., min_length=8, description="Senha deve ter no mínimo 8 caracteres.")  
    profile: UserProfileUpdateAPI # Usar Update aqui para permitir campos opcionais  
    roles: Optional[List[str]] = Field(None, description="Roles iniciais (default 'customer' se omitido).")  
    is_active: bool = True # Default para ativo?

    model_config = ConfigDict(json_schema_extra={  
        "example": {  
            "email": "novo.usuario@email.com",  
            "password": "password123",  
            "profile": {"first_name": "Novo", "last_name": "Usuario"},  
            "roles": ["customer"]  
        }  
    })

class UserUpdateAPI(BaseModel):  
    """Payload para atualizar dados do usuário via API (ex: pelo próprio usuário ou admin)."""  
    # Não permitir atualizar email ou senha aqui (criar endpoints específicos)  
    profile: Optional[UserProfileUpdateAPI] = None  
    # Atualização de roles e status geralmente requer endpoint de admin separado  
    # roles: Optional[List[str]] = None  
    # is_active: Optional[bool] = None

# --- Schemas para RFID ---  
class AddRFIDPayload(BaseModel):  
    tag_id: str = Field(..., description="ID da tag RFID a ser associada.")

    @field_validator('tag_id')  
    @classmethod  
    def tag_id_format(cls, v):  
        # Adicionar validação básica de formato de tag UHF EPC, se conhecido  
        if not v or not v.isalnum() or len(v) < 10: # Exemplo simples  
            raise ValueError("Invalid RFID tag format provided.")  
        return v.upper() # Padronizar para maiúsculas?
