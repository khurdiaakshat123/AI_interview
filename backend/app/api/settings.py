from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from backend.app.llm.client import llm_client

router = APIRouter(prefix="/api/settings", tags=["Settings & LLM Configuration"])

class LLMKeyUpdateRequest(BaseModel):
    gemini_key: Optional[str] = None
    groq_key: Optional[str] = None
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None

@router.get("/llm-status")
def get_llm_status():
    return {
        "active_provider": llm_client.get_active_provider(),
        "has_gemini": bool(llm_client.gemini_key),
        "has_groq": bool(llm_client.groq_key),
        "has_openai": bool(llm_client.openai_key),
        "has_anthropic": bool(llm_client.anthropic_key)
    }

@router.post("/llm-keys")
def update_llm_keys(payload: LLMKeyUpdateRequest):
    llm_client.update_keys(payload.model_dump())
    return {
        "message": "LLM API keys updated successfully",
        "active_provider": llm_client.get_active_provider()
    }
