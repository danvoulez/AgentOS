# ... imports ...
from fastapi import FastAPI, Request, Depends
import httpx
from app.services.llm_service import get_llm_service # or adjust import as needed
from app.utils.opa_validator import validate_via_opa
from app.websocket.connection_manager import ws_manager
from app.config import settings

app = FastAPI(...)

@app.get("/health", tags=["Status"], summary="Perform a health check of the application and its dependencies.")
async def health_check_root(db_for_health = Depends(get_database)):
    results = {"status": "ok", "project": settings.PROJECT_NAME, "version": app.version}
    try: await db_for_health.command('ping'); results["database_status"] = "ok"
    except Exception as e: results["database_status"] = f"error: {type(e).__name__}"
    # OPA Status
    if settings.OPA_URL:
        opa_health_url = str(settings.OPA_URL).rsplit('/',2)[0] + "/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp_opa = await client.get(opa_health_url)
                results["opa_status"] = "ok" if resp_opa.status_code == 200 else f"error_status_{resp_opa.status_code}"
        except Exception as e: results["opa_status"] = f"error_connect: {type(e).__name__}"
    else:
        results["opa_status"] = "not_configured"
    # LLM Status
    llm_service_instance = get_llm_service()
    if settings.LLM_PROVIDER != "mock" and llm_service_instance and getattr(llm_service_instance, "client", None):
        try:
            if settings.LLM_PROVIDER == "openai":
                from openai import AsyncOpenAI
                if isinstance(llm_service_instance.client, AsyncOpenAI):
                    await llm_service_instance.client.models.list(limit=1)
            results["llm_status"] = "ok"
        except Exception as e: results["llm_status"] = f"error_connect: {type(e).__name__}"
    elif settings.LLM_PROVIDER == "mock": results["llm_status"] = "mock_provider"
    else: results["llm_status"] = "not_configured_or_init_failed"
    results["log_level"] = settings.LOG_LEVEL
    results["active_ws_users"] = len(ws_manager.active_connections)
    return results