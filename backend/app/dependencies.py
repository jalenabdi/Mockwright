from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.security import decode_access_token
from .database import get_db
from .models import Interview, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

DbSession = Annotated[Session, Depends(get_db)]


def user_from_token(token: str, db: Session) -> User | None:
    """Return the user a token belongs to, or None if the token is invalid."""
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        return None
    return db.get(User, user_id)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Return the user who owns the bearer token, or raise 401."""
    user = user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def find_owned_interview(db: Session, interview_id: int, user_id: int) -> Interview | None:
    return db.scalar(
        select(Interview).where(Interview.id == interview_id, Interview.user_id == user_id)
    )


def get_owned_interview(interview_id: int, current_user: CurrentUser, db: DbSession) -> Interview:
    """Return the interview only if it belongs to the signed-in user.

    A missing interview and someone else's interview both give the same 404,
    so nobody can learn which interview ids exist.
    """
    interview = find_owned_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    return interview


OwnedInterview = Annotated[Interview, Depends(get_owned_interview)]
