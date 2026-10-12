from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.schemas import HealthResponse, LLMProvidersResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.app_version,
        database=db_status,
    )


@router.get("/llm/providers", response_model=LLMProvidersResponse)
async def get_llm_providers():
    return LLMProvidersResponse(
        providers=["openai", "anthropic", "gemini", "ollama"],
        current=settings.llm_provider,
        model=settings.llm_model,
    )