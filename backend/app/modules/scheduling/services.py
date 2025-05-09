# app/modules/scheduling/services.py
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from bson import ObjectId
from fastapi import HTTPException, status
from loguru import logger
from decimal import Decimal

from .repository import ShiftRepository
from .models import ShiftInDB, ShiftCreateInternal, ShiftUpdateInternal, ShiftAPI
from app.modules.people.repository import UserRepository
from app.modules.people.models import UserInDB
from app.modules.office.services_audit import AuditService

class SchedulingService:

    async def _enrich_shift(self, shift_db: ShiftInDB, user_repo: UserRepository) -> ShiftAPI:
        shift_api = ShiftAPI.model_validate(shift_db)
        user = await user_repo.get_by_id(shift_db.user_id)
        if user and user.profile:
            shift_api.user_details = {"id": str(user.id), "name": f"{user.profile.first_name or ''} {user.profile.last_name or ''}".strip(), "email": user.email}
        else:
            shift_api.user_details = {"id": str(shift_db.user_id), "name": "Unknown User"}
        return shift_api

    async def create_shift(self, shift_in: ShiftCreateInternal, shift_repo: ShiftRepository, user_repo: UserRepository, audit_service: Optional[AuditService] = None, current_user: Optional[UserInDB] = None) -> ShiftAPI:
        log =	logger.bind(service="SchedulingService", user_id=str(shift_in.user_id), date=shift_in.shift_date)
        log.info("Service: Creating new shift...")
        employee = await user_repo.get_by_id(shift_in.user_id)
        if not employee or not employee.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {shift_in.user_id} not found or inactive.")
        created_db = await shift_repo.create(shift_in.model_dump())
        log.success(f"Shift created successfully. ID: {created_db.id}")
        if audit_service and current_user:
            await audit_service.log_audit_event(action="shift_created", status="success", entity_type="Shift", entity_id=created_db.id, audit_repo=None, details=created_db.model_dump(mode='json'), current_user=current_user, request=None)
        return await self._enrich_shift(created_db, user_repo)

    async def list_shifts_for_user(self, user_id: ObjectId, start_date: date, end_date: date, shift_repo: ShiftRepository, user_repo: UserRepository, skip: int = 0, limit: int = 31) -> List[ShiftAPI]:
        shifts_db = await shift_repo.list_shifts_by_user_and_date(user_id, start_date, end_date, skip, limit)
        return [await self._enrich_shift(s, user_repo) for s in shifts_db]

    async def mark_attendance(self, shift_id_str: str, employee_user: UserInDB, shift_repo: ShiftRepository, user_repo: UserRepository, audit_service: Optional[AuditService] = None) -> ShiftAPI:
        shift_id = shift_repo._to_objectid(shift_id_str)
        shift = await shift_repo.get_by_id(shift_id)
        updated = await shift_repo.update(shift_id, ShiftUpdateInternal(status="attended").model_dump(exclude_unset=True))
        return await self._enrich_shift(updated, user_repo)

async def get_scheduling_service() -> SchedulingService:
    return SchedulingService()
