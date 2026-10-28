"""POST /auth/token: verify a user's password and issue a signed JWT.

Week 4 scope is login/token issuance only. Registration (Alex) and the
get_current_user dependency (Marcial) are built on top of this.

Assumed User contract (the User model is not merged yet):
    from backend.app.models.user import User
    User.id              : primary key, used as the JWT "sub" (as str)
    User.email           : str, unique
    User.hashed_password : str, a pwdlib/Argon2 hash
"""

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
