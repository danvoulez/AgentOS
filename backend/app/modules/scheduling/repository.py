# app/modules/scheduling/repository.py
from typing import List, Dict, Any
from datetime import date
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
from loguru import logger
from decimal import Decimal

from app.core.repository import BaseRepository
from .models import ShiftInDB, ShiftCreateInternal, ShiftUpdateInternal
from app.core.database import get_database

COLLECTION_NAME = "shifts"

class ShiftRepository(BaseRepository[ShiftInDB, ShiftCreateInternal, ShiftUpdateInternal]):
    model = ShiftInDB
    collection_name = COLLECTION_NAME

    async def create_indexes(self):
        await self.collection.create_index([("user_id", ASCENDING), ("shift_date", DESCENDING)])
        await self.collection.create_index("shift_date")
        await self.collection.create_index("status")
        await self.collection.create_index([("status", ASCENDING), ("shift_date", ASCENDING)])
        logger.info(f"Indices created/verified for collection: {self.collection_name}")

    def _prepare_data_for_db(self, data: Dict) -> Dict:
        prepared = super()._prepare_data_for_db(data)
        if "paid_amount" in prepared and isinstance(prepared.get("paid_amount"), Decimal):
            prepared["paid_amount"] = str(prepared["paid_amount"])
        return prepared

    async def list_shifts_by_user_and_date(self, user_id: ObjectId, start_date: date, end_date: date, skip: int = 0, limit: int = 31) -> List[ShiftInDB]:
        query = {"user_id": user_id, "shift_date": {"$gte": start_date, "$lte": end_date}}
        sort_order = [("shift_date", ASCENDING), ("start_time", ASCENDING)]
        return await self.list_by(query=query, skip=skip, limit=limit, sort=sort_order)

    async def list_attended_unpaid_shifts(self, for_date: date) -> List[ShiftInDB]:
        query = {"shift_date": for_date, "status": "attended"}
        return await self.list_by(query=query, limit=0, sort=[("user_id", ASCENDING)])

async def get_shift_repository() -> ShiftRepository:
    db = get_database()
    return ShiftRepository(db)
