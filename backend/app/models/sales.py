# agentos_core/app/models/sales.py

from pydantic import BaseModel, Field, field_validator, ConfigDict # field_validator  
from typing import List, Optional, Dict, Any  
from datetime import datetime  
from decimal import Decimal

# Reutilizar PyObjectId e outros modelos  
from app.modules.people.models import PyObjectId

# --- Schemas de Preços (API) ---  
class ProductPricesAPI(BaseModel):  
    """Estrutura de preços para exibição na API (valores como string)."""  
    sale_a: Optional[str] = None  
    sale_b: Optional[str] = None  
    sale_c: Optional[str] = None  
    resale_a: Optional[str] = None  
    resale_b: Optional[str] = None  
    resale_c: Optional[str] = None  
    cost: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) # Para ler do modelo DB

# --- Schemas de Produto (API) ---  
class ProductAPI(BaseModel):  
    """Schema de Produto para respostas da API."""  
    id: PyObjectId  
    name: str  
    description: Optional[str] = None  
    prices: ProductPricesAPI # <<< Retorna preços como string  
    sku: Optional[str] = None  
    is_active: bool  
    is_kit: bool  
    kit_components: Optional[List[Dict[str, Any]]] = None  
    stock_quantity: int = Field(description="Estoque físico total.")  
    reserved_stock: int = Field(description="Estoque reservado para pedidos pendentes.")  
    available_stock: int = Field(description="Estoque disponível para venda (stock - reserved).")  
    # Não incluir price_history na resposta padrão da API? Pode ser grande.  
    # price_history: Optional[List[PriceHistoryEntryAPI]] = Field(None, exclude=True)  
    created_at: datetime  
    updated_at: datetime

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={datetime: lambda v: v.isoformat()},  
         json_schema_extra={  
            "example": {  
                "id": "663b8a11f1a4e7d8c9b1a1b1",  
                "name": "Produto Exemplo Premium",  
                "description": "Descrição detalhada do produto.",  
                "prices": {"sale_a": "199.99", "sale_b": "189.99", "cost": "85.50"},  
                "sku": "PROD-PREMIUM-001",  
                "is_active": True,  
                "is_kit": False,  
                "kit_components": None,  
                "stock_quantity": 100,  
                "reserved_stock": 5,  
                "available_stock": 95,  
                "created_at": "2024-05-08T10:00:00Z",  
                "updated_at": "2024-05-08T11:00:00Z"  
            }  
        }  
    )

class ProductCreateAPI(BaseModel):  
    """Payload para criar um novo produto via API."""  
    name: str = Field(..., min_length=3)  
    description: Optional[str] = None  
    # Receber preços como string para evitar problemas de float  
    prices: Dict[str, Optional[str]] = Field(..., description="Objeto com preços (sale_a, cost, etc.) como strings. Ex: {'sale_a': '100.50', 'cost': '50.00'}")  
    sku: Optional[str] = None  
    is_active: bool = True  
    is_kit: bool = False  
    kit_components: Optional[List[Dict[str, Any]]] = None # Ex: [{"product_id": "...", "quantity": 1}]  
    stock_quantity: int = Field(..., ge=0)

    # Adicionar validação para garantir que as chaves em 'prices' são válidas?  
    # Adicionar validação para garantir que os valores de preço são numéricos?

class ProductUpdateAPI(BaseModel):  
    """Payload para atualizar um produto existente via API."""  
    name: Optional[str] = Field(None, min_length=3)  
    description: Optional[str] = None  
    prices: Optional[Dict[str, Optional[str]]] = Field(None, description="Objeto com preços a serem atualizados (como strings).")  
    sku: Optional[str] = None  
    is_active: Optional[bool] = None  
    is_kit: Optional[bool] = None  
    kit_components: Optional[List[Dict[str, Any]]] = None  
    stock_quantity: Optional[int] = Field(None, ge=0)  
    price_update_reason: Optional[str] = Field(None, description="Obrigatório se 'prices' for atualizado (para histórico).")

# --- Schemas de Item de Pedido (API) ---  
class OrderItemAPI(BaseModel):  
    """Schema de Item de Pedido para respostas da API."""  
    product_id: PyObjectId  
    quantity: int  
    product_name: str  
    price_at_purchase: str # <<< Retornar como string  
    selected_price_tier: str  
    margin_at_purchase: Optional[str] = None # <<< Retornar como string

    model_config = ConfigDict(from_attributes=True)

class OrderItemCreateAPI(BaseModel):  
    """Payload para adicionar item ao criar pedido."""  
    product_id: str # Receber como string  
    quantity: int = Field(..., gt=0)

    @field_validator('product_id')  
    @classmethod  
    def check_product_id(cls, value):  
        if not ObjectId.is_valid(value):  
             raise ValueError("Invalid product_id format.")  
        return value

# --- Schemas de Pedido (API) ---  
class OrderAPI(BaseModel):  
    """Schema principal de Pedido para respostas da API."""  
    id: PyObjectId  
    order_ref: str  
    customer_id: PyObjectId  
    # Opcional: Enriquecer com detalhes do cliente  
    customer_details: Optional[Dict[str, Any]] = None  
    items: List[OrderItemAPI] # <<< Usa OrderItemAPI  
    total_amount: str # <<< Retornar como string  
    status: str  
    channel: Optional[str] = None  
    shipping_address: Optional[Dict[str, Any]] = None  
    billing_address: Optional[Dict[str, Any]] = None  
    delivery_id: Optional[PyObjectId] = None  
    transaction_ids: List[PyObjectId] = []  
    created_at: datetime  
    updated_at: datetime

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={datetime: lambda v: v.isoformat()}  
    )

class OrderCreateAPI(BaseModel):  
    """Payload para criar um novo pedido via API."""  
    # customer_id é pego do usuário logado no endpoint, não precisa vir aqui  
    items: List[OrderItemCreateAPI] # <<< Usa OrderItemCreateAPI  
    shipping_address: Optional[Dict[str, Any]] = None  
    billing_address: Optional[Dict[str, Any]] = None  
    channel: Optional[str] = Field(None, description="Canal de origem da venda (ex: 'ui', 'whatsapp', 'api')")  
    # Opcional: passar perfil para cálculo de preço, se não puder ser inferido do user  
    customer_profile_type: Optional[str] = None

    @field_validator('items')  
    @classmethod  
    def check_items_not_empty(cls, v):  
        if not v: raise ValueError("Order must contain at least one item")  
        return v

class OrderStatusUpdateAPI(BaseModel):  
     """Payload para atualizar o status de um pedido via API."""  
     status: str # TODO: Usar Literal com os status válidos de Order  
     # Adicionar notas se necessário  
     notes: Optional[str] = None

     # @validator('status') ... (validar se é um status permitido)

# Importar ObjectId para validação  
from bson import ObjectId
