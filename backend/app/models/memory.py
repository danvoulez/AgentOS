# agentos_core/app/models/memory.py

from pydantic import BaseModel, Field, ConfigDict  
from typing import List, Optional, Dict, Any  
from datetime import datetime

from app.modules.people.models import PyObjectId # Reutilizar

# --- Schemas para API (se exposto) ou uso interno ---

class MemoryRecordCreateAPI(BaseModel):  
    """Payload para adicionar uma memória via API (se necessário)."""  
    text: str = Field(..., description="Conteúdo textual da memória.")  
    source: Optional[str] = Field(None, description="Origem da memória (ex: chat_session_id, document_id, manual)")  
    tags: List[str] = Field(default=[], description="Tags para filtragem.")  
    user_id: Optional[str] = Field(None, description="ID do usuário associado (se não for o usuário logado).") # Admin pode adicionar para outros?

    model_config = ConfigDict(json_schema_extra={  
        "example": {  
            "text": "Cliente Joana (ID:...) mencionou interesse no produto Y em 15/04.",  
            "source": "chat:session_123",  
            "tags": ["interest", "product_y", "follow_up"],  
            "user_id": "662f1a9fdd8a4b5e6f7d5678"  
        }  
    })

class MemoryRecordAPI(BaseModel):  
    """Schema para retornar um registro de memória via API."""  
    id: PyObjectId = Field(..., description="ID interno da memória")  
    user_id: PyObjectId  
    text: str  
    source: Optional[str] = None  
    tags: List[str] = []  
    created_at: datetime  
    # Opcional: incluir embedding na API? Geralmente não.  
    # embedding: Optional[List[float]] = Field(None, exclude=True)  
    # Incluir score quando for resultado de busca  
    similarity_score: Optional[float] = Field(None, description="Score de similaridade da busca vetorial (se aplicável).")

    model_config = ConfigDict(  
        populate_by_name=True,  
        from_attributes=True,  
        json_encoders={datetime: lambda v: v.isoformat() if v else None}  
    )

class MemorySearchQueryAPI(BaseModel):  
    """Payload para buscar memórias via API (se necessário)."""  
    query_text: str = Field(..., description="Texto para buscar memórias similares.")  
    user_id: Optional[str] = Field(None, description="ID do usuário para buscar memórias (se diferente do logado - admin?).")  
    limit: int = Field(default=5, gt=0, le=20)  
    min_similarity: float = Field(default=0.78, ge=0.0, le=1.0)  
    tags_filter: Optional[List[str]] = None
