# agentos_core/app/models/stock.py

from pydantic import BaseModel, Field, ConfigDict, field_validator  
from typing import List, Optional, Literal, Dict, Any  
from datetime import datetime

# Reutilizar PyObjectId  
from app.modules.people.models import PyObjectId

# Status (consistente com modelo interno)  
STOCK_ITEM_STATUS = Literal[  
    "provisioned", "in_stock", "reserved", "sold",  
    "returned", "damaged", "missing", "in_transit_store", "exited_unverified"  
]

# --- Schemas para API ---

class StockItemAPI(BaseModel):  
    """Schema para retornar um item de estoque individual via API."""  
    id: PyObjectId  
    rfid_tag_id: str  
    product_id: PyObjectId  
    product_name: Optional[str] = Field(None, description="Nome do produto (enriquecido).")  
    product_sku: Optional[str] = Field(None, description="SKU do produto (enriquecido).")  
    status: STOCK_ITEM_STATUS  
    location: Optional[str] = None  
    metadata: Optional[dict] = None  
    created_at: datetime  
    updated_at: datetime  
    last_seen_at: Optional[datetime] = None

    model_config = ConfigDict(  
        from_attributes=True,  
        populate_by_name=True,  
        json_encoders={datetime: lambda v: v.isoformat() if v else None}  
    )

class StockItemCreateAPI(BaseModel):  
    """Payload para cadastrar um único item de estoque via API."""  
    rfid_tag_id: str = Field(..., description="ID da tag RFID a ser associada.")  
    product_id: str = Field(..., description="ID do produto ao qual associar a tag.")  
    initial_status: STOCK_ITEM_STATUS = "provisioned"  
    initial_location: Optional[str] = None  
    metadata: Optional[dict] = None

    @field_validator('product_id')  
    @classmethod  
    def check_product_id(cls, value):  
        if not ObjectId.is_valid(value):  
             raise ValueError("Invalid product_id format.")  
        return value

    # Adicionar validação para rfid_tag_id?

class BulkStockItemCreateAPI(BaseModel):  
    """Payload para cadastro em massa."""  
    items: List[StockItemCreateAPI]

class BulkStockItemResponseAPI(BaseModel):  
     """Resposta do cadastro em massa."""  
     inserted: int  
     modified: int # Upsert pode modificar  
     errors: List[str]

class StockItemUpdateAPI(BaseModel):  
    """Payload para atualizar status/localização manualmente."""  
    status: Optional[STOCK_ITEM_STATUS] = None  
    location: Optional[str] = None  
    metadata: Optional[dict] = None

class RFIDEventAPI(BaseModel):  
    """Payload para o endpoint /rfid/events."""  
    event_type: Literal["stock_update", "access_control", "inventory"]  
    tag_id: str  
    reader_id: str  
    timestamp: Optional[datetime] = None # Opcional, backend pode usar now()  
    location: Optional[str] = None  
    status: Optional[Literal["detected", "disappeared"]] = "detected"  
    rssi: Optional[int] = None

    model_config = ConfigDict(json_schema_extra={  
        "example_stock": {  
            "event_type": "stock_update",  
            "tag_id": "E28011700000020FABC12345",  
            "reader_id": "exit_door_1",  
            "location": "store_exit",  
            "timestamp": "2024-05-08T15:30:00Z",  
            "status": "detected"  
        }  
    })

# Importar ObjectId para validação  
from bson import ObjectId
