# app/modules/memory/models.py

from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

class MemoryBase(BaseModel):
    content: str
    source: Optional[str] = None

class MemoryCreate(MemoryBase):
    tags: Optional[List[str]] = []

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None

class MemoryInDB(MemoryBase):
    id: ObjectId
    tags: List[str] = []

    class Config:
        arbitrary_types_allowed = True
