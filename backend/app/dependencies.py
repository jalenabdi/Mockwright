from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.security import ALGORITHM, SECRET_KEY
from .database import get_db
from .models.interview import Interview
from .models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Return the user who owns the bearer token, or raise 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def get_owned_interview(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> Interview:
    """Return the interview only if it belongs to the signed-in user.

    A missing interview and someone else's interview both give the same 404,
    so nobody can learn which interview ids exist.
    """
    interview = db.scalar(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == current_user.id,
        )
    )
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    return interview