import httpx
import asyncio
from loguru import logger
import sys
from pathlib import Path

def get_settings():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import settings
    return settings

async def run_smoke_tests():
    logger.info("Starting LogLine V2 Smoke Tests...")
    results = {"api": "FAIL", "mongo": "FAIL", "opa": "FAIL", "llm": "FAIL_OR_NOT_CHECKED"}
    settings = get_settings()
    api_base_url = f"http://localhost:{settings.API_PORT_FOR_TESTS or 8001}"
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # 1. API Health
        try:
            resp = await client.get("/health", timeout=5)
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                results["api"] = "OK"
                results["mongo"] = resp.json().get("database_status", "UNKNOWN")
            logger.info(f"API Health: {results['api']}, Mongo Status from API: {results['mongo']}")
        except Exception as e: logger.error(f"API Health Check failed: {e}")

        # 2. OPA Health
        if settings.OPA_URL:
            opa_health_url = str(settings.OPA_URL).rsplit('/',2)[0] + "/health"
            try:
                resp_opa = await client.get(opa_health_url, timeout=3)
                if resp_opa.status_code == 200: results["opa"] = "OK"
                else: results["opa"] = f"WARN (Status: {resp_opa.status_code})"
                logger.info(f"OPA Health ({opa_health_url}): {results['opa']}")
            except Exception as e: logger.error(f"OPA Health Check failed for {opa_health_url}: {e}")

        # 3. LLM Service (ping OpenAI if configured)
        if getattr(settings, "OPENAI_API_KEY", None) and getattr(settings, "LLM_PROVIDER", None) == "openai":
            try:
                from openai import AsyncOpenAI
                llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=5.0)
                await llm_client.models.list(limit=1)
                results["llm"] = "OK"
                logger.info("LLM Connection (OpenAI): OK")
            except Exception as e:
                results["llm"] = f"FAIL ({type(e).__name__})"
                logger.error(f"LLM Connection Check failed: {e}")
        else:
            results["llm"] = "NOT_CONFIGURED"
            logger.info("LLM not configured for smoke test.")

    logger.info(f"Smoke Test Results: {results}")
    if all(v == "OK" or v == "NOT_CONFIGURED" or v.startswith("WARN") for v in results.values()):
        logger.success("All critical smoke tests passed (or services not configured).")
        sys.exit(0)
    else:
        logger.error("One or more smoke tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_smoke_tests())