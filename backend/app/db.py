"""Supabase connection. No route calls it yet: the stubs run on sample data."""
from .config import get_settings


class DatabaseNotConfigured(RuntimeError):
    """SUPABASE_URL or SUPABASE_KEY is missing."""


def get_supabase():
    """Return a Supabase client, or raise DatabaseNotConfigured."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise DatabaseNotConfigured("Set SUPABASE_URL and SUPABASE_KEY (see backend/.env.example).")
    from supabase import create_client  # imported here so the app starts without Supabase

    return create_client(settings.supabase_url, settings.supabase_key)
