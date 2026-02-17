from fastapi import APIRouter

from .analytics import router as events_router
from .analytics import summary_router as analytics_router
from .dashboard import router as dashboard_router
from .flashcards import categories_router
from .flashcards import router as flashcards_router
from .users import router as users_router

api_router = APIRouter()

api_router.include_router(users_router)
api_router.include_router(dashboard_router)
api_router.include_router(flashcards_router)
api_router.include_router(categories_router)
api_router.include_router(events_router)
api_router.include_router(analytics_router)
