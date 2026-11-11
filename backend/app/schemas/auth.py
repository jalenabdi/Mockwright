"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field, field_validator


class Token(BaseModel):
    """Response body for a successful POST /auth/token."""

    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    """Credentials for creating a user account."""

    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Email address used to sign in.",
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password must contain between 8 and 128 characters.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value
