"""Settings come from environment variables (see backend/.env.example)."""
import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Settings:
    cors_origins: List[str]
    supabase_url: str
    supabase_key: str
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_max_tokens: int
    llm_reasoning_effort: str
    llm_timeout: float


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return Settings(
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        llm_base_url=os.getenv(
            "LLM_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        llm_model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
        llm_reasoning_effort=os.getenv("LLM_REASONING_EFFORT", ""),
        llm_timeout=float(os.getenv("LLM_TIMEOUT", "30")),
    )
