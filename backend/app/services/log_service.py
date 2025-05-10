import logging
from fastapi import BackgroundTasks, Depends
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Callable, Dict, Any
import uuid

from app.models import LogEvent, DespachoCreatedData
from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.state_updater import StateUpdaterService, get_state_updater_service, StateUpdateResult
from app.websocket.connection_manager import manager as ws_manager
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class LogService:
    def __init__(self, db: AsyncIOMotorDatabase, state_updater: StateUpdaterService):
        self.db = db
        self.state_updater = state_updater
        logger.info("LogService initialized.")

    async def _record_single_event_core(
        self,
        event_draft: LogEvent,
        background_tasks: BackgroundTasks,
        non_critical_side_effects: Optional[List[Tuple[Callable, List, Dict]]] = None,
    ) -> LogEvent:
        log = logger.bind(event_type=event_draft.type, author=event_draft.author, draft_id=event_draft.id)
        log.info("Core event recording started...")

        if not event_draft.timestamp:
            event_draft.timestamp = datetime.now(timezone.utc)
        if not event_draft.id:
            event_draft.id = f"evt_{uuid.uuid4().hex}"
            log.warning(f"event_draft.id was not set, generated: {event_draft.id}")

        try:
            log_dict_for_db = event_draft.model_dump(exclude_none=True)
            logs_collection = self.db["logs"]
            insert_result = await logs_collection.insert_one(log_dict_for_db)
            log.success(f"LogEvent persisted. System ID: {event_draft.id}, DB _id: {insert_result.inserted_id}")

            state_update_outcome: Optional[StateUpdateResult] = None
            try:
                state_update_outcome = await self.state_updater.update_state(event_draft)
                log.info(f"Synchronous state update completed for event: {event_draft.id}")
            except Exception as state_update_error:
                log.critical(
                    f"CRITICAL FAILURE: State update failed after logging event {event_draft.id}. System may be inconsistent. Error: {state_update_error}",
                    exc_info=True
                )
                raise RuntimeError(f"State update failed for event {event_draft.id}") from state_update_error

            ws_payload_for_fusion = {
                "type": "new_log_event_v2",
                "payload": event_draft.model_dump(mode='json')
            }
            try:
                await ws_manager.broadcast(ws_payload_for_fusion)
                log.debug(f"WebSocket broadcast initiated for event: {event_draft.id}")
            except Exception as ws_err:
                log.error(f"WebSocket broadcast failed for event {event_draft.id}: {ws_err}", exc_info=True)

            if non_critical_side_effects:
                for task_func, task_args, task_kwargs in non_critical_side_effects:
                    try:
                        background_tasks.add_task(task_func, *task_args, **task_kwargs)
                        log.info(f"Added background task: {getattr(task_func, '__name__', 'unknown_task_func')}")
                    except Exception as bg_task_err:
                        log.error(f"Failed to add background task: {bg_task_err}", exc_info=True)

            # --- SYSTEM CONSEQUENCE EVENTS ---
            if state_update_outcome and state_update_outcome.suggested_consequence_events:
                log.info(f"Found {len(state_update_outcome.suggested_consequence_events)} suggested consequence events for {event_draft.id}.")
                for cons_info in state_update_outcome.suggested_consequence_events:
                    cons_event_type = cons_info["event_type"]
                    cons_event_data_model: BaseModel = cons_info["event_data_model"]
                    background_tasks.add_task(
                        self.record_system_consequence_event,
                        consequence_event_type=cons_event_type,
                        consequence_event_data=cons_event_data_model,
                        triggering_event=event_draft,
                    )
                    log.info(f"Scheduled recording of consequence event: Type '{cons_event_type}'")

            return event_draft
        except Exception as e:
            log.exception(f"CRITICAL error during core event recording (type: {event_draft.type}): {e}")
            raise RuntimeError(f"Failed to record event: {e}") from e

    async def record_event(
        self,
        event_draft: LogEvent,
        background_tasks: BackgroundTasks,
        non_critical_side_effects: Optional[List[Tuple[Callable, List, Dict]]] = None
    ) -> LogEvent:
        """
        Primary public method to record a user/externally-initiated event.
        """
        return await self._record_single_event_core(
            event_draft, background_tasks, non_critical_side_effects
        )

    async def record_system_consequence_event(
        self,
        consequence_event_type: str,
        consequence_event_data: BaseModel,
        triggering_event: LogEvent,
        new_background_tasks_instance: Optional[BackgroundTasks] = None
    ) -> Optional[LogEvent]:
        """
        Records a new LogEvent that is a direct system-driven consequence of a preceding event.
        The 'author' is typically a system identifier, and 'witness' is the triggering event.
        """
        log = logger.bind(
            triggering_event_id=triggering_event.id,
            consequence_event_type=consequence_event_type,
            trace_id=triggering_event.meta.get("trace_id") if triggering_event.meta else logger.extra.get("trace_id")
        )
        log.info("Recording system-driven consequence event...")

        meta_for_consequence = {"trace_id": log.extra.get("trace_id")}
        if triggering_event.meta and "conversation_id" in triggering_event.meta:
            meta_for_consequence["conversation_id"] = triggering_event.meta["conversation_id"]
        meta_for_consequence["triggered_by_log_id"] = triggering_event.id

        consequence_draft = LogEvent(
            type=consequence_event_type,
            author="system:state_consequence_engine",
            witness=f"log_event:{triggering_event.id}",
            data=consequence_event_data.model_dump(),
            channel="system_internal",
            origin=f"consequence_of:{triggering_event.type}",
            meta=meta_for_consequence
        )

        bg_tasks_for_consequence = new_background_tasks_instance if new_background_tasks_instance else BackgroundTasks()

        try:
            persisted_consequence_event = await self._record_single_event_core(
                consequence_draft,
                bg_tasks_for_consequence,
                non_critical_side_effects=None
            )
            log.success(f"Successfully recorded consequence event: {persisted_consequence_event.id} (Type: {consequence_event_type})")
            return persisted_consequence_event
        except Exception as e:
            log.critical(f"Failed to record system consequence event of type '{consequence_event_type}' triggered by '{triggering_event.id}': {e}", exc_info=True)
            return None

async def get_log_service(
    db_instance: AsyncIOMotorDatabase = Depends(get_database),
    state_updater: StateUpdaterService = Depends(get_state_updater_service)
) -> LogService:
    return LogService(db_instance, state_updater)