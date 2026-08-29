from contextlib import asynccontextmanager

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
from app.routes.committee import router as committee_router
from app.routes.advances import router as advances_router
from app.utils.seed_data import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.APP_ENV == "development":
        seed_database()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secure, transparent and intelligent community savings management.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(members_router)
app.include_router(contributions_router)
app.include_router(transactions_router)
app.include_router(receipts_router)
app.include_router(ai_router)
app.include_router(audit_router)
app.include_router(analytics_router)
app.include_router(committee_router)
app.include_router(advances_router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": "Secure, Transparent & Intelligent Community Savings Management",
        "hackathon": "Omnikon 2026",
        "problem_statement": "Omni_FinTech_9",
        "status": "online",
        "documentation": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
