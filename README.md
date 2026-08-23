# SaveCircle

> Secure, transparent and intelligent community savings management.

SaveCircle digitizes community savings groups and chit-fund-style records so administrators and members can track contributions, verification, receipts, savings cycles and audit history from one shared system. An explainable risk engine highlights unusual transactions for human review; it never automatically accuses or blocks a member.

**Omnikon 2026 · Omni_FinTech_9 — Digitizing Community Savings Groups Securely**

## Highlights

- Role-based member and administrator access
- Group, membership and savings-cycle management
- Contribution verification and transaction ledger
- Digital receipts and traceable audit records
- Explainable risk alerts with human review
- Responsive React dashboard and documented FastAPI backend
- Synthetic demonstration data only—no real payments are processed

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Recharts |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite for local MVP; PostgreSQL-ready |
| Risk analysis | Python, NumPy, Pandas, Scikit-learn |
| Authentication | JWT and bcrypt |

## Project structure

```text
Save-circle/
├── frontend/              # React + TypeScript client
├── backend/app/           # FastAPI application
│   ├── routes/            # REST endpoints
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Request/response schemas
│   ├── services/          # Authentication, audit, receipts
│   └── ml/                # Explainable transaction-risk engine
├── SaveCircle_PRD.md
└── SaveCircle_Omnikon_Round1.pptx
```

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API: `http://localhost:8000` · Swagger docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
# Create .env and set: VITE_API_URL=http://localhost:8000
npm run dev
```

Frontend: `http://localhost:5173`

## Demo accounts

Local seed data creates these demonstration-only accounts:

| Role | Email | Password |
|---|---|---|
| Administrator | admin@savecircle.demo | Admin@123 |
| Member | member@savecircle.demo | Member@123 |

Do not use these credentials in a production deployment.

## API overview

- `/api/auth` — registration, login and current user
- `/api/groups` — savings groups and cycles
- `/api/members` — membership
- `/api/contributions` — contribution workflow
- `/api/transactions` — ledger
- `/api/receipts` — digital receipts
- `/api/ai` — explainable risk analysis
- `/api/audit` — audit trail
- `/api/analytics` — dashboard metrics

## Responsible AI and data notice

The MVP uses synthetic, fictional demonstration data. Risk results are decision-support signals based on transparent transaction rules and statistical features. They are not fraud verdicts and require administrator review. SaveCircle currently does not move real money or claim regulatory certification.

## Links

- Live demo: [Save_Circle _link](https://savecircle-demo.priyankarawat4622.chatgpt.site).
- Demo video: _Add after recording_
- Round 1 presentation: [SaveCircle_Omnikon_Round1.pptx](./SaveCircle_Omnikon_Round1.pptx)
- Product requirements: [SaveCircle_PRD.md](./SaveCircle_PRD.md)


### Demo Login

- **Email:** `admin@savecircle.demo`
- **Password:** `Admin@123`
## License

Licensed under the [MIT License](./LICENSE).
