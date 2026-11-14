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


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return Settings(
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
    )
