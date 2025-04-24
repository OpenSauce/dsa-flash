"""Aggregate top‑level router so main.py only needs one include_router."""

from fastapi import APIRouter

from .users import router as users_router
from .flashcards import router as flashcards_router

router = APIRouter()
router.include_router(users_router)
router.include_router(flashcards_router)
