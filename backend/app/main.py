from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import api_router
from .database import run_migrations
from .loader import load_yaml_flashcards


@asynccontextmanager
async def lifespan(_):
    run_migrations()
    load_yaml_flashcards()
    yield


app = FastAPI(title="Flashcards API", lifespan=lifespan)


app.include_router(api_router)
