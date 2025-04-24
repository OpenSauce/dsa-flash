from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from ..database import get_session
from ..models import Token, User, UserCreate

SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_SECRET"  # in prod: os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["users"])


# ---------- helpers ----------


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()


def authenticate_user(session: Session, username: str, password: str):
    user = get_user(session, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict) -> str:
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
):
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise cred_exc
    except JWTError:
        raise cred_exc
    user = get_user(session, username)
    if user is None:
        raise cred_exc
    return user


# ---------- endpoints ----------


@router.post("/signup", status_code=201)
def signup(data: UserCreate, session: Session = Depends(get_session)):
    if get_user(session, data.username):
        raise HTTPException(400, "Username already taken")
    user = User(
        username=data.username, hashed_password=get_password_hash(data.password)
    )
    session.add(user)
    session.commit()
    return {"msg": "user created"}


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(401, "Incorrect username or password")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token}
