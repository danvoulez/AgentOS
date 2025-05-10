from datetime import timedelta
from app.models import (
    LogEvent, LogAcionadoInstitucionalmenteData, LitigioInstitucionalInfo, StateUpdateResult
)
from app.config import settings

class StateUpdaterService:
    # ... existing methods ...

    async def _handle_log_acionado_institucionalmente(self, event: LogEvent, result_obj_for_state: StateUpdateResult):
        log = logger.bind(event_id=event.id, handler="_handle_log_acionado_institucionalmente")
        try:
            event_data = LogAcionadoInstitucionalmenteData(**event.data)
        except Exception as e:
            log.error(f"Malformed event.data: {e}")
            raise

        # 1. Adicionar info do litígio ao CurrentState do objeto principal afetado pelo target_log_id
        target_log_doc = await self.db["logs"].find_one({"id": event_data.target_log_id})
        if not target_log_doc:
            log.warning(f"Target log {event_data.target_log_id} not found.")
            return
        from app.models import LogEvent as LogEventModel
        target_info = await self._determine_main_state_collection_and_id(LogEventModel(**target_log_doc))
        if target_info:
            target_collection_name, target_object_id = target_info
            litigio_info = LitigioInstitucionalInfo(
                log_acionamento_event_id=event.id,
                acionamento_type=event_data.acionamento_type,
                author_acionamento=event.author,
                timestamp_acionamento=event.timestamp,
                motivo=event_data.motivo_detalhado,
                status_litigio="aberto"
            )
            await self.db[target_collection_name].update_one(
                {"_id": target_object_id},
                {
                    "$push": {"litigios_institucionais": {"$each": [litigio_info.model_dump()], "$slice": -5}},
                    "$set": {
                        f"meta.litigio_status.{event_data.acionamento_type.replace('.','_')}": "aberto",
                        "meta.has_active_litigio": True,
                        "last_log_event_id": event.id, "last_updated_at": event.timestamp
                    }
                }
            )
        # 2. Sugerir despacho (simplificado: omite despacho para foco no litígio)