from fastapi import APIRouter
from .users import router as users_router
from .flashcards import router as flashcards_router

api_router = APIRouter()

api_router.include_router(users_router)
api_router.include_router(flashcards_router)
