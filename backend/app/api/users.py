# app/api/users.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from sqlmodel import Field, Session, SQLModel, select

from ..database import get_session
from ..models import StreakOut, StudySession, Token, User, UserCreate

# ─── CONFIG ──────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("DEV_MODE", "").lower() in ("1", "true"):
        SECRET_KEY = "dev-only-not-for-production"
    else:
        raise RuntimeError("SECRET_KEY environment variable is not set or empty")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

router = APIRouter()


# ─── HELPERS ──────────────────────────────────────────────────────────────


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()


def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = get_user(session, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise cred_exc
    except PyJWTError:
        raise cred_exc

    user = get_user(session, username)
    if user is None:
        raise cred_exc
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    request: Request,
    session: Session = Depends(get_session),
) -> Optional[User]:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        token = request.cookies.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
    except PyJWTError:
        return None
    return get_user(session, username)


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    tags=["auth"],
)
def signup(
    data: UserCreate,
    session: Session = Depends(get_session),
):
    if get_user(session, data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
    )
    session.add(user)
    session.commit()
    access_token = create_access_token({"sub": data.username})
    return {"access_token": access_token}


@router.post(
    "/token",
    response_model=Token,
    tags=["auth"],
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token}


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["auth"],
)
def logout(response: Response):
    response.delete_cookie("token")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── “WHO AM I” ENDPOINT ───────────────────────────────────────────────────


class UserRead(SQLModel):
    name: str = Field(validation_alias="username")
    is_admin: bool = False


@router.get(
    "/users/me",
    response_model=UserRead,
    tags=["users"],
)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return UserRead.model_validate(current_user)


@router.get(
    "/users/streak",
    response_model=StreakOut,
    tags=["users"],
)
def get_streak(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    today = datetime.now(timezone.utc).date()

    today_row = session.exec(
        select(StudySession).where(
            StudySession.user_id == current_user.id,
            StudySession.study_date == today,
        )
    ).first()
    today_reviewed = today_row.cards_reviewed if today_row else 0

    rows = session.exec(
        select(StudySession.study_date)
        .where(StudySession.user_id == current_user.id)
        .order_by(StudySession.study_date.desc())
    ).all()

    current_streak = 0
    longest_streak = 0

    if rows:
        # Current streak: walk backwards from today (or yesterday if today not studied yet)
        expected = today
        if not today_row and rows[0] == today - timedelta(days=1):
            expected = today - timedelta(days=1)
        elif not today_row:
            expected = None

        if expected is not None:
            for d in rows:
                if d == expected:
                    current_streak += 1
                    expected -= timedelta(days=1)
                elif d < expected:
                    break

        # Longest streak: scan all dates (never cleared)
        sorted_dates = sorted(set(rows))
        streak = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

    longest_streak = max(longest_streak, current_streak)

    return StreakOut(
        current_streak=current_streak,
        longest_streak=longest_streak,
        today_reviewed=today_reviewed,
    )
