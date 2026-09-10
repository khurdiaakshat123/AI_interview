from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base, SessionLocal
from backend.app.seed.seed_data import seed_database
from backend.app.api import (
    auth_router,
    role_profiles_router,
    practice_router,
    mock_oa_router,
    interview_router,
    admin_router,
)
from backend.app.api.settings import router as settings_router
from backend.app.api.candidate import router as candidate_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Intervyn API",
    description="AI-Powered OA & Mock Interview Preparation Platform with Deterministic Scoring & 18-Point Verification",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router)
app.include_router(candidate_router)
app.include_router(role_profiles_router)
app.include_router(practice_router)
app.include_router(mock_oa_router)
app.include_router(interview_router)
app.include_router(admin_router)
app.include_router(settings_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Intervyn API",
        "version": "1.0.0",
        "agents": [
            "Agent 1: Role Topic Profile Generator",
            "Agent 2: Practice Question Engine",
            "Agent 3: Mock OA Engine",
            "Agent 4: 18-Point Review & Validation",
            "Agent 5: Evaluation & Feedback Engine",
            "Interview Agent 1: Project Defense",
            "Interview Agent 2: Subject/Fundamental Knowledge"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
