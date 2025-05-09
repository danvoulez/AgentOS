# agentos_core/app/models/api_common.py

from pydantic import BaseModel, Field  
from typing import Optional, List, Dict, Any

class StatusResponse(BaseModel):  
    """Resposta genérica indicando o status de uma operação."""  
    status: str = Field(..., description="Status geral (ex: 'ok', 'error', 'success', 'failure', 'accepted')")  
    message: Optional[str] = Field(None, description="Mensagem descritiva opcional.")

class DetailResponse(BaseModel):  
    """Resposta genérica para erros com mais detalhes."""  
    detail: str = Field(..., description="Mensagem detalhada do erro.")

class ErrorDetail(BaseModel):  
     """Estrutura para detalhar erros de validação."""  
     field: Optional[str | int | List[str | int]] = None # Path do campo com erro (pode ser aninhado)  
     message: str # Mensagem de erro específica do campo

class ValidationErrorResponse(BaseModel):  
     """Resposta para erros de validação (HTTP 422)."""  
     detail: str = "Validation Error"  
     errors: List[ErrorDetail]

class AcceptedResponse(BaseModel):  
    """Resposta para operações aceitas para processamento assíncrono."""  
    status: str = "accepted"  
    message: str = "Request accepted for processing."  
    job_id: Optional[str] = Field(None, description="ID da tarefa/job em background (ex: Celery task ID).")

class PaginatedResponse(BaseModel):  
    """Wrapper genérico para respostas paginadas."""  
    total_items: int = Field(..., description="Número total de itens disponíveis.")  
    items: List[Any] # A lista de itens reais (o tipo será definido no endpoint)  
    limit: int = Field(..., description="Número máximo de itens por página.")  
    skip: int = Field(..., description="Número de itens pulados (offset).")  
    # Opcional: Adicionar links prev/next  
    # prev: Optional[str] = None  
    # next: Optional[str] = None
