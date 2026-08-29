from contextlib import asynccontextmanager
import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.finance import CommitteeSettings
from app.models.group import GroupMember, SavingsCycle, SavingsGroup
from app.models.user import User
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


def ensure_live_demo_group():
    """Create a minimal demo savings group when a production SQLite database is empty.

    Local and Render SQLite databases are separate. This keeps the deployed demo usable
    after a fresh/ephemeral Render database starts, without overwriting any real groups.
    """
    db = SessionLocal()
    try:
        if db.query(SavingsGroup).count() > 0:
            return

        admin = db.query(User).filter(User.email == "admin@savecircle.demo").first()
        member = db.query(User).filter(User.email == "member@savecircle.demo").first()
        owner = member or admin
        if not owner:
            return

        group = SavingsGroup(
            name="SaveCircle Demo Savings Group",
            description="Live demo committee for contributions, advances, interest rules and settlement tracking.",
            contribution_amount=2000.0,
            contribution_frequency="Monthly",
            max_members=10,
            current_cycle=1,
            total_cycles=12,
            start_date=datetime.datetime.utcnow(),
            is_active=True,
            created_by_id=owner.id,
        )
        db.add(group)
        db.flush()

        db.add(GroupMember(
            group_id=group.id,
            user_id=owner.id,
            role_in_group="CREATOR",
            is_active=True,
        ))
        db.add(SavingsCycle(
            group_id=group.id,
            cycle_number=1,
            target_amount=group.contribution_amount,
            collected_amount=0.0,
            status="ACTIVE",
            start_date=group.start_date,
        ))
        db.add(CommitteeSettings(
            group_id=group.id,
            normal_interest_rate=1.0,
            overdue_interest_rate=2.0,
            repayment_period_months=6,
            bank_interest_rate=0.0,
        ))
        db.commit()
        print("[+] Created minimal live demo savings group for empty production database.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.APP_ENV == "development":
        seed_database()
    else:
        ensure_live_demo_group()
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
