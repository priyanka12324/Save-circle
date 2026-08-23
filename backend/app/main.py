from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes.auth import router as auth_router
from app.routes.groups import router as groups_router
from app.routes.members import router as members_router
from app.routes.contributions import router as contributions_router
from app.routes.transactions import router as transactions_router
from app.routes.receipts import router as receipts_router
from app.routes.ai import router as ai_router
from app.routes.audit import router as audit_router
from app.routes.analytics import router as analytics_router
from app.utils.seed_data import seed_database

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SaveCircle: Secure, Transparent & Intelligent Community Savings Management FinTech API for Omnikon Hackathon 2026."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(members_router)
app.include_router(contributions_router)
app.include_router(transactions_router)
app.include_router(receipts_router)
app.include_router(ai_router)
app.include_router(audit_router)
app.include_router(analytics_router)

@app.on_event("startup")
def on_startup():
    """Seed sample data on startup if not already seeded."""
    seed_database()

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": "Secure, Transparent & Intelligent Community Savings Management",
        "hackathon": "OMNIKON HACKATHON 2026",
        "problem_statement": "Omni_FinTech_9 - Digitizing Community Savings Groups Securely",
        "status": "online",
        "documentation": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
