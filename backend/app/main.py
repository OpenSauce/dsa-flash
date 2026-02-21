from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api import api_router
from .database import run_migrations
from .limiter import limiter
from .loader import load_lessons, load_yaml_flashcards


@asynccontextmanager
async def lifespan(_):
    run_migrations()
    load_yaml_flashcards()
    load_lessons()
    yield


app = FastAPI(title="Flashcards API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(api_router)
