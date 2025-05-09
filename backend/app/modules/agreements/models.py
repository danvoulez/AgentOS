# app/modules/agreements/models.py

from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

class AgreementBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_active: bool = True

class AgreementCreate(AgreementBase):
    pass

class AgreementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class AgreementInDB(AgreementBase):
    id: ObjectId

    class Config:
        arbitrary_types_allowed = True
