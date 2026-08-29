# SaveCircle

> **Secure, transparent and intelligent community savings management.**

**Omnikon 2026 Finalist · Omni_FinTech_9 — Digitizing Community Savings Groups Securely**

SaveCircle is a full-stack FinTech prototype that digitizes community savings groups and committee/chit-fund-style records. It gives members, group creators and platform administrators one transparent system for contributions, payment-proof verification, digital receipts, committee cycles, advances/withdrawals, repayments, interest tracking, audit history and explainable AI-assisted transaction-risk review.

> **Important:** SaveCircle is a demonstration prototype. It records and verifies simulated payment/contribution information but does not hold funds, move real money, or independently verify bank/UPI payments.

## Live Application

- **Frontend:** https://save-circle-a26t.vercel.app/
- **Backend API:** https://save-circle.onrender.com
- **Swagger API Docs:** https://save-circle.onrender.com/docs
- **Health Check:** https://save-circle.onrender.com/health

## Core Features

### Role-based access
SaveCircle uses a three-level access model:

- **Platform Admin** — oversees the complete platform and can manage/verify across groups.
- **Group Creator** — creates and manages their own savings group, members and contribution verification.
- **Member** — joins savings groups, submits contributions and payment proof, views receipts and can request a committee advance/withdrawal.

### Savings groups and committee cycles
- Create configurable savings groups.
- Set contribution amount, maximum members and total number of cycles.
- Configure normal interest, overdue interest, repayment period and bank-interest assumption.
- Track active members, current cycle, verified savings and group activity.
- Dynamic cycle-by-cycle committee ledger generated from database records rather than hardcoded tables.

### Contribution and payment-proof workflow
1. Member selects a group and submits a contribution.
2. Member records the payment method and transaction/UTR reference.
3. Member uploads a payment-proof screenshot.
4. Contribution enters **Pending Verification**.
5. Group Creator or Platform Admin reviews the contribution and proof.
6. Verified contribution is added to savings totals.
7. SaveCircle generates a traceable digital receipt.

### Committee Ledger
The Committee Ledger provides a dynamic financial view of each configured cycle, including:

- Expected contribution
- Actual verified contribution
- Missing contribution
- Total cash received
- Advance/withdrawal issued
- Advance recipient
- Principal repayment
- Committee interest
- Bank interest
- Outstanding advance balance
- Current bank/cash position
- Member settlement information

### Advance / Withdraw from Committee
Members can request temporary access to part of the available committee pool.

- Member submits an **Advance / Withdraw** request with amount and reason.
- Group Creator/Admin approves or rejects the request.
- Approved advances are tracked against the member.
- Principal and interest repayments can be recorded.
- Default configurable rules support **1% normal interest**, **2% overdue interest**, and a **6-month repayment period**.
- Outstanding principal and realized interest feed back into the Committee Ledger.

### Explainable AI-assisted risk alerts
SaveCircle includes a hybrid explainable risk engine using transaction rules and statistical anomaly detection.

- Rule-based transaction checks
- Isolation Forest when sufficient historical data is available
- Risk score and LOW / MEDIUM / HIGH classification
- Human-readable reasons and recommended action
- Human-in-the-loop review — the system does not automatically accuse or block a member

### Security and traceability
- JWT authentication
- bcrypt password hashing
- Role-based authorization
- CORS configuration for deployed frontend/backend
- Audit trail for important actions
- Digital receipt records
- Environment-based configuration

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| ORM / Data | SQLAlchemy |
| MVP Database | SQLite |
| AI / ML | NumPy, Pandas, Scikit-learn, Isolation Forest |
| Authentication | JWT, bcrypt |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |

## System Architecture

```text
Users
  │
  ▼
React + Vite + TypeScript Frontend
  │
  ▼
FastAPI REST API
  │
  ├── Authentication & Role Authorization
  ├── Savings Groups & Membership
  ├── Contributions & Payment Proof
  ├── Digital Receipts & Audit Trail
  ├── Committee Ledger
  ├── Advance / Withdrawal & Repayment
  └── Explainable AI Risk Engine
  │
  ▼
SQLAlchemy Database Layer
```

## Project Structure

```text
Save-circle/
├── frontend/                 # React + TypeScript application
├── backend/app/
│   ├── routes/               # REST API endpoints
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Request/response schemas
│   ├── services/             # Auth, audit and receipt services
│   └── ml/                   # Explainable risk engine
├── SaveCircle_PRD.md
├── SaveCircle_Omnikon_Round1.pptx
├── LICENSE
└── README.md
```

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Platform Admin | `admin@savecircle.demo` | `Admin@123` |
| Member | `member@savecircle.demo` | `Member@123` |

These accounts and the seeded records are for demonstration purposes only.

## API Overview

- `/api/auth` — registration, login and current user
- `/api/groups` — savings groups, membership and cycles
- `/api/contributions` — contribution and verification workflow
- `/api/transactions` — financial transaction records
- `/api/receipts` — digital receipts
- `/api/groups/{group_id}/advances` — advance/withdrawal requests
- `/api/advances/{advance_id}/decision` — approve/reject an advance
- `/api/advances/{advance_id}/repayments` — record repayment
- `/api/committee` — dynamic committee ledger and settlement data
- `/api/ai` — explainable transaction-risk analysis
- `/api/audit` — audit trail
- `/api/analytics` — dashboard metrics

## Run Locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Backend: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
# Set VITE_API_URL=http://localhost:8000 in .env if required
npm run dev
```

Frontend: `http://localhost:5173`

## Deployment

Production architecture:

```text
Vercel Frontend
https://save-circle-a26t.vercel.app
        │
        ▼
Render FastAPI Backend
https://save-circle.onrender.com
        │
        ▼
SQLAlchemy / MVP Database
```

For a production-scale release, the MVP database should be migrated from SQLite to a persistent managed PostgreSQL database and uploaded payment proofs should use durable object storage.

## Responsible AI & Financial Disclaimer

SaveCircle uses synthetic/fictional demonstration data for evaluation. AI risk results are decision-support signals, not fraud verdicts. Administrative review remains mandatory. SaveCircle does not operate as a bank, does not custody user funds, and does not claim regulatory certification.

## Future Scalability

- Managed PostgreSQL database
- Durable cloud storage for payment proof
- Payment-provider / UPI gateway integration with webhook-based confirmation
- Notifications and reminders for pending/overdue contributions
- Stronger ML evaluation and explainability monitoring
- Dispute and governance workflows
- Multilingual/mobile experience
- Production observability and security hardening

## Project Links

- **Live Demo:** https://save-circle-a26t.vercel.app/
- **Backend API:** https://save-circle.onrender.com
- **API Documentation:** https://save-circle.onrender.com/docs
- **Project Presentation:** [SaveCircle Omnikon Presentation](./SaveCircle_Omnikon_Round1.pptx)
- **Product Requirements:** [SaveCircle_PRD.md](./SaveCircle_PRD.md)
- **PPT** [app explaination](https://docs.google.com/presentation/d/1IzEOrX2IAbYq-CUC4qu9hwxTh6PhJVS8/edit?usp=sharing&ouid=117767666886122076028&rtpof=true&sd=true
  )

## License

Licensed under the [MIT License](./LICENSE).
