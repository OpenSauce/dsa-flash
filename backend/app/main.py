from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, create_engine, Session, select
import os, dotenv

dotenv.load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/flashcards")
engine = create_engine(DATABASE_URL, echo=True)

app = FastAPI(title="DSA Flashcards API")

class Flashcard(SQLModel, table=True):
    id: int | None = SQLModel.field(primary_key=True, default=None)
    question: str
    answer: str

# Dependency for routes

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/flashcards", response_model=list[Flashcard])
def list_cards(session: Session = Depends(get_session)):
    return session.exec(select(Flashcard)).all()

@app.post("/flashcards", response_model=Flashcard)
def add_card(card: Flashcard, session: Session = Depends(get_session)):
    session.add(card)
    session.commit()
    session.refresh(card)
    return card
