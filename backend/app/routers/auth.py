"""Authenticate users and issue signed access tokens."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import DUMMY_PASSWORD_HASH, create_access_token, verify_password
from ..database import get_db
from ..models.user import User
from ..schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["auth"])

INCORRECT_CREDENTIALS_DETAIL = "Incorrect email or password"


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> Token:
    """Verify the submitted email/password and return a signed JWT.

    The OAuth2 form's "username" field holds the user's email, normalized
    the same way as registration (stripped and lowercased). A wrong email
    and a wrong password return the same 401 and message; an unknown email
    still runs a password verification against a dummy hash, so response
    time doesn't reveal whether the email is registered.
    """
    email = form_data.username.strip().lower()
    if (
        len(email) > 254
        or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is None
        or not form_data.password
        or len(form_data.password) > 128
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide a valid email address and a password of at most 128 characters.",
        )

    user = db.scalar(select(User).where(User.email == email))

    if user is not None:
        password_ok = verify_password(form_data.password, user.hashed_password)
    else:
        verify_password(form_data.password, DUMMY_PASSWORD_HASH)
        password_ok = False

    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INCORRECT_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")
