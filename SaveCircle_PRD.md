# Product Requirements Document: SaveCircle

**Tagline:** Secure, Transparent & Intelligent Community Savings Management
**Hackathon:** Omnikon 2026 · Problem ID: `Omni_FinTech_9` — Digitizing Community Savings Groups Securely
**Document status:** Draft for Round 1 · Team Name: *[TO BE FILLED]* · College/University: *[TO BE FILLED]*
**Owner:** *[TO BE FILLED]*

---

## 1. Overview

Traditional chit funds and community savings groups run on trust and paper records. A single treasurer or administrator collects contributions in cash and logs them in a notebook, and every member's view of "who paid what, and when" depends entirely on that record and that person's memory. This creates real vulnerability to disputes and fraud, exactly as identified in the official problem statement.

**SaveCircle** is a secure digital platform for managing community savings groups end-to-end: member management, contribution tracking, payment verification, transaction history, savings cycles, digital receipts, and audit records — replacing paper and single-person trust with a shared, tamper-resistant, always-available record.

As a proposed enhancement beyond the core problem statement, SaveCircle also includes an **AI/ML-based risk detection layer** that flags unusual transaction patterns for administrator review. This layer is decision-support only: it never blocks a transaction or auto-labels a member as fraudulent.

---

## 2. Problem Statement (Official, Omni_FinTech_9)

> "Traditional chit funds and community savings groups operate largely on trust and paper records, leaving them vulnerable to disputes and fraud. Build a secure digital solution for managing these groups."

**Who is affected:**
- The **group administrator / treasurer**, who manually tracks contributions, verifies payments, and manages payouts.
- **Group members**, who depend on the administrator's records and have no independent way to verify their own history.
- The **savings group as a whole**, whose collective trust and continuity depend on unreliable, non-auditable recordkeeping.

**Root causes:**
| Current situation | Gap it creates | Consequence |
|---|---|---|
| Paper records | Difficult to track and reconcile | Disputes among members |
| Manual verification | Weak accountability | Fraud risk |
| Scattered records | Poor transparency | Mistrust in the group |
| No centralized history | Difficult to audit | Unresolved conflicts |

---

## 3. Goals & Non-Goals

### 3.1 Goals (Round 1 scope, maps to problem statement)
- Replace paper-based group and contribution tracking with a secure digital system.
- Give every member independent, verifiable visibility into their own contribution history.
- Make transaction records tamper-resistant and auditable, with all corrections going through a controlled process rather than silent edits.
- Reduce disputes by giving the group a single, shared source of truth.
- Support the full lifecycle of a savings group: creation, membership, contribution rules, savings cycles, and payouts.

### 3.2 Goals (Team-proposed enhancement)
- Add an AI/ML anomaly-detection layer that flags transactions which deviate from a member's typical amount, frequency, or timing, and routes them to the administrator for review — never for automatic action.

### 3.3 Non-Goals (explicitly out of scope for Round 1)
- Real banking or payment-gateway integration; no real money moves through the MVP.
- Automatic fraud accusation, transaction blocking, or account suspension by the AI layer.
- Regulatory or compliance certification of any kind.
- Multi-currency or cross-border group support.
- Native mobile apps (web-based platform only for Round 1).
- Claims of a specific AI model accuracy — the model will be evaluated, but no accuracy figure is committed to at this stage.

---

## 4. Users & Personas

| Persona | Description | Primary needs |
|---|---|---|
| **Group Administrator** | Creates and runs a savings group; historically the sole record-keeper | Create groups, define contribution rules, verify payments, manage savings cycles, review AI-flagged transactions |
| **Group Member** | Contributes funds on a recurring basis | Make contributions, view personal history, receive digital receipts, trust that records are accurate |
| **Savings Group / Community** | The group as a collective unit | A shared, trustworthy, always-available record that reduces disputes and supports continuity |

---

## 5. Functional Requirements

### 5.1 Core Features (required by the problem statement)
- User registration and login
- Group creation and management
- Member management (add/remove members, member profiles)
- Contribution rules configuration (amount, frequency, cycle length)
- Contribution tracking and payment status
- Transaction history per member and per group
- Savings cycle management (start, track, close a cycle)
- Digital receipt generation for each contribution
- Admin dashboard (group overview, pending verifications, cycle status)

### 5.2 Security Features (required by the problem statement)
- Password hashing for all stored credentials
- Role-based access control (Administrator vs. Member permissions)
- Transaction verification step before a contribution is marked confirmed
- Audit logs capturing who did what, and when, across the system
- Tamper-resistant transaction history (append-only where possible; no silent edits)
- A controlled modification/correction process for legitimate record fixes, itself logged in the audit trail

### 5.3 AI/ML Enhancement (team-proposed, additional to the problem statement)
- Transaction anomaly detection based on a member's historical amount, frequency, and timing
- Risk scoring per flagged transaction
- Unusual-behavior alerts surfaced to the administrator
- Explainable reasoning attached to each alert (why it was flagged)
- Human-in-the-loop review: the AI never auto-rejects a transaction or auto-labels a member as fraudulent — it only informs the administrator's decision

**Example:** a member who typically contributes ₹2,000/month and suddenly submits ₹20,000 would be flagged for administrator review based on amount, frequency, timing, and historical pattern — not auto-blocked.

---

## 6. Core User Flow

```
Admin creates group
   ↓
Members join
   ↓
Contribution rules are defined
   ↓
Members make contributions
   ↓
Transactions are recorded and verified
   ↓
Digital receipts are generated
   ↓
Savings cycle is tracked
   ↓
All activity is recorded in an audit trail
   ↓
AI risk engine flags unusual transaction patterns for review
```

---

## 7. System Architecture

```
Users (Admins & Members)
   ↓
Frontend — HTML / CSS / JavaScript
   ↓
Backend API — Python / Flask
   ↓
Authentication & Authorization
   ↓
Application Services
   ├── Group Management
   ├── Member Management
   ├── Contribution Management
   ├── Transaction Management
   ├── Savings Cycle Management
   └── Audit Logging
   ↓
Database — SQLite (MVP) → PostgreSQL (scalable deployment)
   ↓
AI Risk Detection Engine — Python + Scikit-learn
   ↓
Risk Score & Alerts
   ↓
Admin Review Dashboard
```

The AI Risk Detection Engine sits alongside the core system: it reads transaction data and returns a risk score and explanation, which routes to the Admin Review Dashboard. It has no ability to block a transaction or take automatic action on an account.

---

## 8. Proposed Tech Stack

*(Proposed for Round 1 — not yet fully implemented; working code is not mandatory at this stage.)*

| Layer | Proposed Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | SQLite (MVP) → PostgreSQL (production / scaling) |
| Machine Learning | Python, Pandas, NumPy, Scikit-learn |
| Visualization | Chart.js or Plotly |
| Security | Password hashing, authentication, role-based access control, audit logging |
| Version Control | Git + GitHub |
| Deployment | Render / Railway / Vercel (target to be finalized based on final architecture) |

---

## 9. Non-Functional Requirements

- **Security:** all credentials hashed; role-based access enforced on every endpoint; audit log entries immutable once written.
- **Transparency:** every member can view their own full contribution and receipt history at any time.
- **Traceability:** every state-changing action (contribution, verification, correction, cycle close) is attributable to a user and timestamped.
- **Auditability:** administrators and, where appropriate, members can review the audit trail for a group without depending on a single person's memory.
- **Usability:** the interface should be understandable by users with basic digital literacy, consistent with the target population of community savings groups.
- **Scalability:** the data layer is designed to move from SQLite (MVP/demo) to PostgreSQL without a redesign, to support real-world deployment.

---

## 10. Data Considerations

- Round 1 development and testing will use **synthetic or anonymized data only** — no real banking or payment data will be used or claimed.
- No claim of regulatory approval or compliance is made at this stage.
- The AI model's performance will be evaluated during development; no specific accuracy figure is claimed until that evaluation is complete.

---

## 11. Success Metrics (indicative, for future phases)

Since Round 1 does not require a working product, these are intended outcomes to validate once the MVP is built, not current claims:

- Reduction in time administrators spend on manual reconciliation.
- Proportion of contributions verified digitally without dispute.
- Member engagement with personal history/receipt views.
- Precision/recall of the anomaly-detection layer against a labeled synthetic dataset, and the proportion of flags administrators find useful on review.

---

## 12. Implementation Roadmap

| Phase | Focus | Key items |
|---|---|---|
| **1 — UI & Authentication** | Foundation | Registration/login, user roles, dashboard shell |
| **2 — Core Savings Management** | Problem-statement core | Groups, members, contributions, payment status, savings cycles |
| **3 — Security & Transparency** | Problem-statement core | Transaction verification, audit logs, digital receipts, controlled corrections |
| **4 — AI/ML** | Team enhancement | Dataset preparation, feature engineering, anomaly detection, risk scoring, explainable alerts |
| **5 — Testing & Deployment** | Hardening | Security testing, functional testing, model evaluation, deployment, documentation |

This is a planning roadmap for subsequent rounds, not a claim that any phase is already complete.

---

## 13. Risks & Assumptions

| Risk / Assumption | Mitigation |
|---|---|
| AI flags could be misread as fraud accusations | UI and workflow explicitly frame flags as "for review," never as verdicts; explainability shown alongside every alert |
| Synthetic data may not fully represent real transaction patterns | Clearly label MVP results as based on synthetic/anonymized data; revisit with real (consented) data in later phases |
| Low digital literacy among some target users | Prioritize a simple, minimal-text UI; consider assisted-onboarding flows in later phases |
| SQLite won't scale to production load | Architecture is designed for a straightforward migration path to PostgreSQL |

---

## 14. Open Questions

- Final deployment target (Render vs. Railway vs. Vercel) — to be decided based on backend hosting needs.
- Whether payout/disbursement tracking needs its own workflow beyond contribution tracking (candidate for a later phase).
- Exact scope of the controlled correction/modification process (who can approve corrections, and what triggers a review).

---

## 15. Reviewer Notes

- This project is proposed as a secure digital platform for community savings groups, directly addressing Omni_FinTech_9.
- AI-based anomaly detection is an enhancement to the core digitization solution, not part of the official problem statement.
- The AI system is intended to support human review rather than automatically label users as fraudulent.
- The initial version can use a controlled, anonymized, or synthetic dataset for development and testing.
- The architecture is designed to be scalable toward real-world deployment.
- The project focuses on transparency, security, traceability, and responsible use of AI.
