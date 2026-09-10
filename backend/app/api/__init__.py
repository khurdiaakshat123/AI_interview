from backend.app.api.auth import router as auth_router
from backend.app.api.role_profiles import router as role_profiles_router
from backend.app.api.practice import router as practice_router
from backend.app.api.mock_oa import router as mock_oa_router
from backend.app.api.interview import router as interview_router
from backend.app.api.admin import router as admin_router

__all__ = [
    "auth_router",
    "role_profiles_router",
    "practice_router",
    "mock_oa_router",
    "interview_router",
    "admin_router",
]
