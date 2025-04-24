from fastapi import FastAPI

from .api import router as api_router
from .database import init_db
from .loader import load_yaml_flashcards

app = FastAPI(title="Flashcards API")


@app.on_event("startup")
def startup() -> None:
    init_db()
    load_yaml_flashcards()


app.include_router(api_router)
