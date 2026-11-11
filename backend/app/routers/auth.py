"""Registration, login (JWT issuance) and the current-user endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_and_update_password,
    verify_password,
)
from ..dependencies import CurrentUser, DbSession
from ..models import User
from ..schemas.auth import RegisterRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

INCORRECT_CREDENTIALS_DETAIL = "Incorrect email or password"
DUPLICATE_EMAIL_DETAIL = "An account with this email already exists."


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    """Create an account. Passwords are stored only as Argon2 hashes."""
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMAIL_DETAIL)

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two sign-ups with the same email at the same moment.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMAIL_DETAIL)
    db.refresh(user)
    return user


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """Verify email/password and return a signed JWT.

    The OAuth2 form's "username" field holds the email. A wrong email and a
    wrong password return the same 401, and an unknown email still runs a
    hash check so response time does not reveal registered emails.
    """
    email = form_data.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is not None:
        password_ok, new_hash = verify_and_update_password(form_data.password, user.hashed_password)
        if password_ok and new_hash is not None:
            user.hashed_password = new_hash  # move older hashes to the current, faster settings
            db.commit()
    else:
        verify_password(form_data.password, DUMMY_PASSWORD_HASH)
        password_ok = False

    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INCORRECT_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(subject=str(user.id)), token_type="bearer")


@router.get("/me", response_model=UserOut)
def read_me(current_user: CurrentUser) -> User:
    return current_user
