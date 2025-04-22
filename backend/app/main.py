from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlmodel import Session, select
from sqlalchemy import func
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .database import engine
from .loader import load_yaml_flashcards
from .models import Flashcard, User, UserCreate, Token

# ─── config for JWT ─────────────────────────────────────────────────
SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


# ─── create all tables + load flashcards ──────────────────────────────
@app.on_event("startup")
def on_startup():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    load_yaml_flashcards()

# ─── helper to hash & verify passwords ────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ─── get DB session & fetch user ─────────────────────────────────────
def get_session():
    return Session(engine)

def get_user(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()

# ─── authenticate & create JWT ───────────────────────────────────────
def authenticate_user(session: Session, username: str, password: str):
    user = get_user(session, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# ─── dependency to retrieve current user from token ──────────────────
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(session, username)
    if user is None:
        raise credentials_exception
    return user

# ─── signup endpoint ─────────────────────────────────────────────────
@app.post("/signup", status_code=201)
def signup(data: UserCreate, session: Session = Depends(get_session)):
    if get_user(session, data.username):
        raise HTTPException(400, "Username already taken")
    user = User(username=data.username, hashed_password=get_password_hash(data.password))
    session.add(user)
    session.commit()
    return {"msg":"user created"}

# ─── token endpoint ──────────────────────────────────────────────────
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token}

# ─── list flashcards, randomize, require auth ─────────────────────────
@app.get("/flashcards", response_model=list[Flashcard])
def list_cards(
    current_user: User = Depends(get_current_user),
    *,
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    tag: Optional[str]      = Query(None),
    random: bool            = Query(False, description="Shuffle the cards"),
    page: int               = Query(1, ge=1),
    page_size: int          = Query(20, ge=1, le=100),
):
    stmt = select(Flashcard)
    if category:
        stmt = stmt.where(Flashcard.category == category)
    if language:
        stmt = stmt.where(Flashcard.language == language)
    if tag:
        stmt = stmt.where(Flashcard.tags.any(tag))
    if random:
        stmt = stmt.order_by(func.random())

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    cards = Session(engine).exec(stmt).all()
    if not cards and page > 1:
        raise HTTPException(404, "Page out of range")
    return JSONResponse(content=jsonable_encoder(cards))
