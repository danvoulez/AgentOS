# app/modules/scheduling/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import List, Optional
from datetime import date, time
from bson import ObjectId
from pymongo import DESCENDING

from app.core.security import CurrentUser, require_role
from app.modules.people.repository import UserRepository, get_user_repository
from app.modules.office.services_audit import AuditService, get_audit_service
from .services import SchedulingService, get_scheduling_service
from .repository import ShiftRepository, get_shift_repository
from .models import ShiftAPI, MarkAttendanceResponse, SHIFT_STATUSES
from pydantic import BaseModel, Field, field_validator

class ShiftCreateAPI(BaseModel):
    user_id: str = Field(...)
    shift_date: date
    start_time: time
    end_time: time
    status: Optional[SHIFT_STATUSES] = "scheduled"

    @field_validator('user_id')
    @classmethod
    def validate_id(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid user_id")
        return v

scheduling_router = APIRouter()

@scheduling_router.get("/me", response_model=List[ShiftAPI], tags=["Scheduling"])
async def get_my_schedule(start_date: date = Query(...), end_date: date = Query(...), current_user: CurrentUser = Depends(), sched_service: SchedulingService = Depends(get_scheduling_service), shift_repo: ShiftRepository = Depends(get_shift_repository), user_repo: UserRepository = Depends(get_user_repository)):
    return await sched_service.list_shifts_for_user(user_id=current_user.id, start_date=start_date, end_date=end_date, shift_repo=shift_repo, user_repo=user_repo)

scheduling_router.patch("/{shift_id}/attend", response_model=MarkAttendanceResponse, tags=["Scheduling"])
async def mark_attendance(shift_id: str = Path(...), current_user: CurrentUser = Depends(), sched_service: SchedulingService = Depends(get_scheduling_service), shift_repo: ShiftRepository = Depends(get_shift_repository), user_repo: UserRepository = Depends(get_user_repository), audit_service: AuditService = Depends(get_audit_service)):
    return await sched_service.mark_attendance(shift_id, current_user, shift_repo, user_repo, audit_service)
