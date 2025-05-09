# app/modules/tasks/models.py

from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_done: bool = False
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None
    due_date: Optional[datetime] = None

class TaskInDB(TaskBase):
    id: ObjectId

    class Config:
        arbitrary_types_allowed = True
