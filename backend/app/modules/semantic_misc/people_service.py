# modules/people_service.py
import logging
from typing import Dict, Any
import asyncio

logger = logging.getLogger(__name__)

async def create_contact(entities: Dict[str, Any], user_id: str | None = None) -> Dict[str, Any]:
    name = entities.get("name", "Default Name")
    logger.info(f"[PeopleService] Creating contact: Name='{name}'")
    await asyncio.sleep(0.2) # Simulate DB call latency
    contact_id = f"contact_{abs(hash(name))}"
    return {
        "status": "success",
        "message": f"Contact '{name}' created.",
        "contact_id": contact_id
    }
