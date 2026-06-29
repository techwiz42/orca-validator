"""Shared FastAPI dependencies (bootstrap auth = a single shared API key)."""
import secrets

from fastapi import Header, HTTPException, status

from backend.app.config import get_settings


async def require_api_key(authorization: str = Header(default="")) -> str:
    expected = f"Bearer {get_settings().API_KEY}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
    return "api-key-subject"  # bootstrap: a single subject (multi-tenant identity is later)
