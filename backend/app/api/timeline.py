import logging
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.auth import CurrentUser, require_role
from app.models import LogEvent, TimelineQueryResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "",
    response_model=TimelineQueryResponse,
    dependencies=[Depends(require_role(["admin", "manager", "auditor"]))],
    summary="Query the full LogLine history (Audit Trail)"
)
async def get_log_timeline(
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    skip: int = Query(0, ge=0, description="Number of events to skip."),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events to return."),
    event_type: Optional[str] = Query(None, alias="type", description="Filter by event type (e.g., 'registrar_venda')."),
    author: Optional[str] = Query(None, description="Filter by author ID (e.g., 'user:email@...')."),
    witness: Optional[str] = Query(None, description="Filter by witness ID."),
    channel: Optional[str] = Query(None, description="Filter by channel."),
    origin: Optional[str] = Query(None, description="Filter by origin."),
    start_timestamp: Optional[datetime] = Query(None, alias="start_ts", description="Filter events from this UTC timestamp (inclusive). ISO format."),
    end_timestamp: Optional[datetime] = Query(None, alias="end_ts", description="Filter events up to this UTC timestamp (exclusive). ISO format."),
    data_contains_key: Optional[str] = Query(None, description="Filter if 'data' field contains this key (dot notation for nested, e.g., 'order_details.customer_id')."),
    data_value_match: Optional[str] = Query(None, description="If 'data_contains_key' is set, its value must match this string (exact match).")
):
    log = logger.bind(user_id=str(current_user.id), trace_id=logger.extra.get("trace_id"))
    log.info("Querying immutable LogLine timeline.")

    query_filter: Dict[str, Any] = {}
    if event_type: query_filter["type"] = event_type
    if author: query_filter["author"] = author
    if witness: query_filter["witness"] = witness
    if channel: query_filter["channel"] = channel
    if origin: query_filter["origin"] = origin

    ts_filter = {}
    if start_timestamp: ts_filter["$gte"] = start_timestamp
    if end_timestamp: ts_filter["$lt"] = end_timestamp
    if ts_filter: query_filter["timestamp"] = ts_filter

    if data_contains_key:
        key_path = f"data.{data_contains_key}"
        if data_value_match is not None:
            try:
                query_value = int(data_value_match)
            except ValueError:
                try:
                    query_value = float(data_value_match)
                except ValueError:
                    query_value = data_value_match
            query_filter[key_path] = query_value
        else:
            query_filter[key_path] = {"$exists": True}

    log.debug(f"Timeline query filter constructed: {query_filter}")
    try:
        logs_collection = db["logs"]
        total_count = await logs_collection.count_documents(query_filter)
        cursor = logs_collection.find(query_filter).sort("timestamp", -1).skip(skip).limit(limit)
        log_docs = await cursor.to_list(length=limit)

        events = []
        for doc in log_docs:
            try:
                events.append(LogEvent(**doc))
            except Exception as e:
                log.warning(f"Skipping LogEvent parse error: ID {doc.get('id')}, Type {doc.get('type')}, Error: {e}")

        return TimelineQueryResponse(events=events, total_count=total_count, limit=limit, skip=skip)
    except Exception as e:
        log.exception("Error querying timeline logs.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve timeline data.")

@router.get(
    "/{log_event_id}",
    response_model=LogEvent,
    dependencies=[Depends(require_role(["staff", "admin", "manager", "auditor"]))],
    summary="Get a specific LogEvent by its system ID"
)
async def get_specific_log_event(
    log_event_id: str,
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    log = logger.bind(user_id=str(current_user.id), log_event_id=log_event_id, trace_id=logger.extra.get("trace_id"))
    log.info("Fetching specific LogEvent by system ID.")
    log_doc = await db["logs"].find_one({"id": log_event_id})

    if not log_doc:
        log.warning("LogEvent not found by system ID.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LogEvent not found.")

    try:
        return LogEvent(**log_doc)
    except Exception as e:
        log.error(f"Error parsing LogEvent from DB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving LogEvent data.")