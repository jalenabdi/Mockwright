"""Pydantic schemas for the auth endpoints."""

from pydantic import BaseModel


class Token(BaseModel):
    """Response body for a successful POST /auth/token."""

    access_token: str
    token_type: str
