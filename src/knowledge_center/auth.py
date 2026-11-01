"""Register, login, and the `CurrentUser` dependency used by protected endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from knowledge_center.db import DbConn
from knowledge_center.schemas import Token, UserCreate, UserOut
from knowledge_center.security import (
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Reads the "Authorization: Bearer <token>" header. tokenUrl tells Swagger's
# "Authorize" button where to log in.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USER_COLUMNS = "id, email, full_name, created_at"


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], conn: DbConn) -> UserOut:
    user_id = read_access_token(token)
    row = None
    if user_id is not None:
        row = conn.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in, or the session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserOut(**row)


# Use as a parameter type: `def endpoint(user: CurrentUser)` makes the endpoint
# require login and gives you the signed-in user.
CurrentUser = Annotated[UserOut, Depends(get_current_user)]


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, conn: DbConn) -> UserOut:
    email = data.email.lower()
    existing = conn.execute("SELECT 1 FROM users WHERE email = %s", (email,)).fetchone()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    row = conn.execute(
        f"""
        INSERT INTO users (email, password_hash, full_name)
        VALUES (%s, %s, %s)
        RETURNING {USER_COLUMNS}
        """,
        (email, hash_password(data.password), data.full_name),
    ).fetchone()
    return UserOut(**row)


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], conn: DbConn) -> Token:
    # The OAuth2 form calls the field "username"; we use the email there.
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = %s",
        (form.username.strip().lower(),),
    ).fetchone()

    password_hash = row["password_hash"] if row else None
    if not verify_password(form.password, password_hash):
        # Same message for unknown email and wrong password, so attackers
        # can't find out which emails have accounts.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    return Token(access_token=create_access_token(str(row["id"])))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return user
