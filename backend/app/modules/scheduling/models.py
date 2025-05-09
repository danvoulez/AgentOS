# app/modules/scheduling/models.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, date, time
from bson import ObjectId
from decimal import Decimal

from app.models.api_common import PyObjectId

SHIFT_STATUSES = Literal["scheduled", "confirmed", "attended", "no_show", "paid", "cancelled"]

class ShiftBase(BaseModel):
    user_id: ObjectId = Field(...)
    shift_date: date = Field(...)
    start_time: time = Field(...)
    end_time: time = Field(...)
    location: Optional[str] = Field(None, description="Optional location identifier")

    @field_validator('end_time')
    @classmethod
    def check_end_time(cls, v: time, info):
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('End time must be after start time')
        return v

class ShiftCreateInternal(ShiftBase):
    status: SHIFT_STATUSES = "scheduled"
    notes: Optional[str] = None

class ShiftUpdateInternal(BaseModel):
    status: Optional[SHIFT_STATUSES] = None
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_amount: Optional[Decimal] = None

    model_config = ConfigDict(extra='ignore')

class ShiftInDB(ShiftBase):
    id: PyObjectId = Field(..., alias="_id")
    status: SHIFT_STATUSES
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_amount: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, datetime: lambda dt: dt.isoformat(), date: lambda d: d.isoformat(), time: lambda t: t.isoformat()}
    )

class ShiftAPI(BaseModel):
    id: str
    user_id: str
    user_details: Optional[Dict[str, Any]] = Field(None, description="Enriched employee details")
    shift_date: date
    start_time: time
    end_time: time
    status: SHIFT_STATUSES
    location: Optional[str] = None
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_amount: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda dt: dt.isoformat() if dt else None, date: lambda d: d.isoformat(), time: lambda t: t.isoformat()}
    )

class ScheduleListParams(BaseModel):
    user_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[SHIFT_STATUSES] = None

class MarkAttendanceResponse(BaseModel):
    status: str = "success"
    message: str
    shift_id: str
    new_shift_status: SHIFT_STATUSES
