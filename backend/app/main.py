from fastapi import FastAPI
from contextlib import asynccontextmanager
from .api import api_router
from .database import init_db
from .loader import load_yaml_flashcards


@asynccontextmanager
async def lifespan(_):
    init_db()
    load_yaml_flashcards()
    yield


app = FastAPI(title="Flashcards API", lifespan=lifespan)


app.include_router(api_router)
