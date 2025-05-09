# agentos_core/app/models/banking.py

from pydantic import BaseModel, Field, field_validator, ConfigDict # Usar field_validator em Pydantic v2  
from typing import Optional, Literal  
from datetime import datetime  
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Usar PyObjectId do módulo people para consistência  
from app.modules.people.models import PyObjectId

# Tipos e Status (manter consistência com modelo interno)  
TRANSACTION_TYPES = Literal[  
    "sale_income", "refund_outgoing", "expense_operational",  
    "commission_payout", "payment_received", "other_income", "other_expense"  
]  
TRANSACTION_STATUSES = Literal["pending", "completed", "failed", "cancelled"]

# --- Schemas para API ---

class TransactionCreateAPI(BaseModel):  
    """Payload para criar uma nova transação (via API Admin/Sistema)."""  
    type: TRANSACTION_TYPES  
    # Receber amount como string para evitar problemas de float na API  
    amount_str: str = Field(..., alias="amount", description="Valor da transação (positivo para entradas, negativo para saídas). Ex: '100.50', '-25.00'")  
    currency: str = Field(default="BRL", max_length=3)  
    description: str = Field(..., min_length=3)  
    status: TRANSACTION_STATUSES = "completed" # Default ou pode ser 'pending'?  
    associated_order_id: Optional[str] = None # Receber como string  
    associated_user_id: Optional[str] = None # Receber como string

    _normalized_amount: Decimal | None = None # Campo privado para guardar valor validado

    # Validador para converter string para Decimal e validar regras de sinal  
    @field_validator('amount_str')  
    @classmethod  
    def validate_and_normalize_amount(cls, value: str, info) -> str: # info contém o dict de valores  
        """Valida o formato do amount, converte para Decimal e guarda."""  
        if not isinstance(value, str): # Segurança extra  
             raise ValueError("Amount must be provided as a string.")  
        try:  
            amount_decimal = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  
            if amount_decimal == Decimal('0.0'):  
                raise ValueError("Transaction amount cannot be zero.")

            # Guardar valor decimal validado para validação cruzada com 'type'  
            # Usar o contexto de validação (requer Pydantic v2 avançado ou truque)  
            # Abordagem mais simples: validar tipo vs sinal em um validador root

            # Retornar string original ou string formatada? Manter original por enquanto.  
            return value  
        except InvalidOperation:  
            raise ValueError("Invalid format for amount. Use string like '123.45'.")

    @field_validator('associated_order_id', 'associated_user_id')  
    @classmethod  
    def check_objectid_format(cls, value: Optional[str]):  
        """Valida se o ID (se fornecido) parece um ObjectId."""  
        if value is not None and not ObjectId.is_valid(value):  
             raise ValueError(f"Invalid ObjectId format for association: {value}")  
        return value

    # TODO: Adicionar validador root para checar sinal de amount vs type

    model_config = ConfigDict(  
        json_schema_extra={  
            "example": {  
                "type": "sale_income",  
                "amount": "199.90",  
                "currency": "BRL",  
                "description": "Venda Online Pedido #ORD-2025-00123",  
                "status": "completed",  
                "associated_order_id": "662fc1bacc8a4b5e6f7d1234",  
                "associated_user_id": "662f1a9fdd8a4b5e6f7d5678"  
            }  
        }  
    )

class TransactionUpdateAPI(BaseModel):  
    """Payload para atualizar campos permitidos de uma transação."""  
    status: Optional[TRANSACTION_STATUSES] = None  
    description: Optional[str] = None

    model_config = ConfigDict(  
        json_schema_extra={  
            "example": {  
                "status": "failed",  
                "description": "Pagamento recusado pela operadora."  
            }  
        }  
    )

class TransactionAPI(BaseModel):  
    """Schema para retornar dados de transação via API."""  
    id: PyObjectId = Field(..., description="ID interno da transação")  
    transaction_ref: str = Field(..., description="Referência única da transação (TRX-...).")  
    type: TRANSACTION_TYPES  
    # Retornar amount como string para consistência  
    amount: str = Field(..., description="Valor da transação.")  
    currency: str  
    description: str  
    status: TRANSACTION_STATUSES  
    associated_order_id: Optional[PyObjectId] = None  
    associated_user_id: Optional[PyObjectId] = None  
    timestamp: datetime # Data/hora do registro da transação

    model_config = ConfigDict(  
        populate_by_name = True, # Permite mapear _id para id  
        from_attributes=True, # Permite criar de objetos DB/Pydantic internos  
        json_encoders={ datetime: lambda dt: dt.isoformat() } # Formatar datas  
    )

# Importar ObjectId para validação  
from bson import ObjectId
