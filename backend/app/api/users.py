# app/api/users.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Field, Session, SQLModel, select

from ..database import get_session
from ..models import Token, User, UserCreate

# ─── CONFIG ──────────────────────────────────────────────────────────────

SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_SECRET"  # override from env in prod
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
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
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
    except JWTError:
        raise cred_exc

    user = get_user(session, username)
    if user is None:
        raise cred_exc
    return user


async def get_optional_user(
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
    except JWTError:
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
    return {"msg": "User created"}


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


@router.get(
    "/users/me",
    response_model=UserRead,
    tags=["users"],
)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return UserRead.from_orm(current_user)
