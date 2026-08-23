import json
import uuid
import datetime
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.group import SavingsGroup, GroupMember, SavingsCycle
from app.models.transaction import Contribution, Transaction, DigitalReceipt
from app.models.audit import AuditLog
from app.models.risk_alert import RiskAlert
from app.services.auth_service import get_password_hash
from app.services.receipt_service import generate_digital_receipt
from app.ml.detector import detector

def seed_database():
    print("[+] Initializing SaveCircle Database Schema...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Check if already seeded
    admin_exists = db.query(User).filter(User.email == "admin@savecircle.demo").first()
    if admin_exists:
        print("[*] Database already populated with seed data.")
        db.close()
        return

    print("[+] Seeding Demo Users...")
    # 1. Admin Account
    admin = User(
        full_name="Rajesh Sharma (Admin)",
        email="admin@savecircle.demo",
        phone="+91 98765 43210",
        hashed_password=get_password_hash("Admin@123"),
        role="ADMIN",
        is_active=True
    )
    db.add(admin)

    # 2. Main Member Account
    demo_member = User(
        full_name="Priya Patel",
        email="member@savecircle.demo",
        phone="+91 98111 22334",
        hashed_password=get_password_hash("Member@123"),
        role="MEMBER",
        is_active=True
    )
    db.add(demo_member)

    # 3. 20 Realistic Fictional Community Members
    sample_members_data = [
        ("Aarav Mehta", "aarav.mehta@demo.in", "+91 98220 11001"),
        ("Ananya Deshmukh", "ananya.d@demo.in", "+91 98220 11002"),
        ("Rohan Verma", "rohan.verma@demo.in", "+91 98220 11003"),
        ("Sneha Kulkarni", "sneha.k@demo.in", "+91 98220 11004"),
        ("Vikramaditya Rao", "vikram.rao@demo.in", "+91 98220 11005"),
        ("Pooja Nair", "pooja.nair@demo.in", "+91 98220 11006"),
        ("Amitabh Sengupta", "amitabh.s@demo.in", "+91 98220 11007"),
        ("Deepika Joshi", "deepika.j@demo.in", "+91 98220 11008"),
        ("Siddharth Malhotra", "sid.m@demo.in", "+91 98220 11009"),
        ("Meera Nambiar", "meera.n@demo.in", "+91 98220 11010"),
        ("Kavita Iyer", "kavita.iyer@demo.in", "+91 98220 11011"),
        ("Gaurav Bansal", "gaurav.b@demo.in", "+91 98220 11012"),
        ("Sunita Reddy", "sunita.r@demo.in", "+91 98220 11013"),
        ("Naveen Choudhury", "naveen.c@demo.in", "+91 98220 11014"),
        ("Pooja Hegde", "pooja.h@demo.in", "+91 98220 11015"),
        ("Karan Johar", "karan.j@demo.in", "+91 98220 11016"),
        ("Shreya Ghoshal", "shreya.g@demo.in", "+91 98220 11017"),
        ("Harish Bhat", "harish.b@demo.in", "+91 98220 11018"),
        ("Divya Dutta", "divya.d@demo.in", "+91 98220 11019"),
        ("Manish Pandey", "manish.p@demo.in", "+91 98220 11020"),
    ]

    all_users = [admin, demo_member]
    for name, email, phone in sample_members_data:
        u = User(
            full_name=name,
            email=email,
            phone=phone,
            hashed_password=get_password_hash("Demo@123"),
            role="MEMBER",
            is_active=True
        )
        db.add(u)
        all_users.append(u)

    db.commit()
    for u in all_users:
        db.refresh(u)

    print(f"[+] Seeded {len(all_users)} Users (1 Admin, 21 Members).")

    # 4. Create 3 Savings Groups
    print("[+] Seeding 3 Community Savings Groups...")
    group1 = SavingsGroup(
        name="Dehradun Community Savings",
        description="Neighborhood monthly chit and cooperative savings pool founded for local welfare and emergency micro-credits.",
        contribution_amount=2000.0,
        contribution_frequency="Monthly",
        max_members=20,
        current_cycle=4,
        total_cycles=12,
        start_date=datetime.datetime.utcnow() - datetime.timedelta(days=120),
        is_active=True,
        created_by_id=admin.id
    )
    group2 = SavingsGroup(
        name="Greenfield Women Self-Help Pool",
        description="Empowering local women entrepreneurs through monthly rotating capital and peer-guaranteed financial security.",
        contribution_amount=1500.0,
        contribution_frequency="Monthly",
        max_members=15,
        current_cycle=3,
        total_cycles=10,
        start_date=datetime.datetime.utcnow() - datetime.timedelta(days=90),
        is_active=True,
        created_by_id=admin.id
    )
    group3 = SavingsGroup(
        name="Metro Tech Founders Chit",
        description="High-trust technology founders peer fund for mutual project collateral and angel milestone guarantees.",
        contribution_amount=5000.0,
        contribution_frequency="Monthly",
        max_members=12,
        current_cycle=2,
        total_cycles=12,
        start_date=datetime.datetime.utcnow() - datetime.timedelta(days=60),
        is_active=True,
        created_by_id=admin.id
    )

    groups = [group1, group2, group3]
    db.add_all(groups)
    db.commit()
    for g in groups:
        db.refresh(g)

    # 5. Create Savings Cycles for Groups
    cycles = []
    for g in groups:
        for c_num in range(1, g.current_cycle + 1):
            c_status = "COMPLETED" if c_num < g.current_cycle else "ACTIVE"
            cycle = SavingsCycle(
                group_id=g.id,
                cycle_number=c_num,
                target_amount=g.contribution_amount * g.max_members,
                collected_amount=0.0,
                status=c_status,
                start_date=g.start_date + datetime.timedelta(days=(c_num - 1) * 30),
                end_date=g.start_date + datetime.timedelta(days=c_num * 30) if c_status == "COMPLETED" else None
            )
            db.add(cycle)
            cycles.append(cycle)
    db.commit()
    for c in cycles:
        db.refresh(c)

    # 6. Enroll Members into Groups
    print("[+] Enrolling Members into Groups...")
    # Demo member is in Group 1 and Group 2
    db.add(GroupMember(group_id=group1.id, user_id=demo_member.id, role_in_group="MEMBER"))
    db.add(GroupMember(group_id=group2.id, user_id=demo_member.id, role_in_group="MEMBER"))

    # Enroll other members
    members_only = [u for u in all_users if u.role == "MEMBER" and u.id != demo_member.id]
    for idx, m in enumerate(members_only):
        if idx < 16:
            db.add(GroupMember(group_id=group1.id, user_id=m.id, role_in_group="MEMBER"))
        if 8 <= idx < 18:
            db.add(GroupMember(group_id=group2.id, user_id=m.id, role_in_group="MEMBER"))
        if idx >= 12:
            db.add(GroupMember(group_id=group3.id, user_id=m.id, role_in_group="MEMBER"))
    db.commit()

    # 7. Seed Regular Historical Contributions & Verified Digital Receipts
    print("[+] Seeding Historical Verified Contributions & Digital Receipts...")
    methods = ["UPI (Demo)", "Bank Transfer (Demo)", "Cash (Demo)"]
    tx_count = 0

    # Seed past cycles for Group 1
    g1_members = db.query(GroupMember).filter(GroupMember.group_id == group1.id).all()
    for c_idx in range(1, 4):  # cycles 1, 2, 3
        c_obj = next((c for c in cycles if c.group_id == group1.id and c.cycle_number == c_idx), None)
        cycle_date = group1.start_date + datetime.timedelta(days=(c_idx - 1) * 30 + 5)
        for gm in g1_members[:12]:
            tx_ref = f"TXN-DEMO-{cycle_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
            contrib = Contribution(
                member_id=gm.user_id,
                group_id=group1.id,
                cycle_id=c_obj.id if c_obj else None,
                amount=2000.0,
                payment_method=methods[gm.user_id % 3],
                transaction_ref=tx_ref,
                status="VERIFIED",
                notes="Standard monthly contribution",
                verified_by_id=admin.id,
                verified_at=cycle_date + datetime.timedelta(hours=2),
                created_at=cycle_date
            )
            db.add(contrib)
            db.commit()
            db.refresh(contrib)

            # Transaction Ledger
            tx = Transaction(
                reference_id=tx_ref,
                member_id=gm.user_id,
                group_id=group1.id,
                amount=2000.0,
                type="CONTRIBUTION",
                status="COMPLETED",
                description=f"Verified monthly contribution to {group1.name}",
                created_at=cycle_date
            )
            db.add(tx)
            db.commit()

            # Digital Receipt
            generate_digital_receipt(db, contrib, admin)
            if c_obj:
                c_obj.collected_amount += 2000.0
            tx_count += 1

    # Seed some contributions for Group 2
    g2_members = db.query(GroupMember).filter(GroupMember.group_id == group2.id).all()
    for gm in g2_members[:8]:
        tx_ref = f"TXN-DEMO-G2-{uuid.uuid4().hex[:6].upper()}"
        contrib = Contribution(
            member_id=gm.user_id,
            group_id=group2.id,
            amount=1500.0,
            payment_method="UPI (Demo)",
            transaction_ref=tx_ref,
            status="VERIFIED",
            notes="Regular monthly quota",
            verified_by_id=admin.id,
            verified_at=datetime.datetime.utcnow() - datetime.timedelta(days=15),
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=16)
        )
        db.add(contrib)
        db.commit()
        db.refresh(contrib)

        tx = Transaction(
            reference_id=tx_ref,
            member_id=gm.user_id,
            group_id=group2.id,
            amount=1500.0,
            type="CONTRIBUTION",
            status="COMPLETED",
            description=f"Verified contribution to {group2.name}",
            created_at=contrib.created_at
        )
        db.add(tx)
        db.commit()
        generate_digital_receipt(db, contrib, admin)
        tx_count += 1

    # 8. Seed 4 Specific AI Flagged Anomaly Transactions for Live Demonstration
    print("[+] Seeding 4 Specific AI Flagged Anomalies for Interactive Evaluation...")
    
    # Anomaly Case 1: Extreme Magnitude Spike (₹20,000 vs ₹2,000 standard - 10x deviation)
    u_spike = members_only[1]  # Ananya Deshmukh
    tx1_ref = f"TXN-ANOM-SPIKE-{uuid.uuid4().hex[:6].upper()}"
    tx1 = Transaction(
        reference_id=tx1_ref,
        member_id=u_spike.id,
        group_id=group1.id,
        amount=20000.0,
        type="CONTRIBUTION",
        status="FLAGGED",
        description=f"Manual Demo deposit of ₹20,000 to {group1.name}",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
    )
    db.add(tx1)
    db.commit()
    db.refresh(tx1)

    c_spike = Contribution(
        member_id=u_spike.id,
        group_id=group1.id,
        amount=20000.0,
        payment_method="Bank Transfer (Demo)",
        transaction_ref=tx1_ref,
        status="PENDING",
        notes="Advance bulk payment demo",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
    )
    db.add(c_spike)
    db.commit()

    alert1 = RiskAlert(
        transaction_id=tx1.id,
        member_id=u_spike.id,
        member_name=u_spike.full_name,
        group_id=group1.id,
        group_name=group1.name,
        amount=20000.0,
        risk_level="HIGH",
        anomaly_score=0.88,
        reasons_json=json.dumps([
            {"indicator": "+", "type": "FLAG", "message": "Transaction amount (₹20,000.00) is 10.0x higher than standard group requirement (₹2,000.00)."},
            {"indicator": "+", "type": "FLAG", "message": "Sudden 900% deviation from member's historical average contribution."},
            {"indicator": "-", "type": "POSITIVE", "message": "Member has 3 previous verified on-time cycle payments."}
        ]),
        recommended_action="Administrator manual verification required before ledger entry",
        status="PENDING_REVIEW"
    )
    db.add(alert1)

    # Anomaly Case 2: High Velocity Burst (Multiple transactions in rapid succession)
    u_burst = members_only[4]  # Vikramaditya Rao
    tx2_ref = f"TXN-ANOM-BURST-{uuid.uuid4().hex[:6].upper()}"
    tx2 = Transaction(
        reference_id=tx2_ref,
        member_id=u_burst.id,
        group_id=group1.id,
        amount=6000.0,
        type="CONTRIBUTION",
        status="FLAGGED",
        description=f"Third contribution submitted within 24 hours to {group1.name}",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    )
    db.add(tx2)
    db.commit()
    db.refresh(tx2)

    c_burst = Contribution(
        member_id=u_burst.id,
        group_id=group1.id,
        amount=6000.0,
        payment_method="UPI (Demo)",
        transaction_ref=tx2_ref,
        status="PENDING",
        notes="Multiple sub-cycle entries",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    )
    db.add(c_burst)
    db.commit()

    alert2 = RiskAlert(
        transaction_id=tx2.id,
        member_id=u_burst.id,
        member_name=u_burst.full_name,
        group_id=group1.id,
        group_name=group1.name,
        amount=6000.0,
        risk_level="MEDIUM",
        anomaly_score=0.55,
        reasons_json=json.dumps([
            {"indicator": "+", "type": "FLAG", "message": "Transaction velocity spike: 3 distinct submissions detected in under 24 hours."},
            {"indicator": "+", "type": "FLAG", "message": "Amount (₹6,000.00) represents a 3.0x multiple of current cycle rule."},
            {"indicator": "-", "type": "POSITIVE", "message": "Verified active phone and KYC credentials on file."}
        ]),
        recommended_action="Administrator review recommended to verify duplicate deposit slip",
        status="PENDING_REVIEW"
    )
    db.add(alert2)

    # Anomaly Case 3: First-time Member High Outlier in Tech Chit
    u_first = members_only[14]  # Pooja Hegde
    tx3_ref = f"TXN-ANOM-FIRST-{uuid.uuid4().hex[:6].upper()}"
    tx3 = Transaction(
        reference_id=tx3_ref,
        member_id=u_first.id,
        group_id=group3.id,
        amount=25000.0,
        type="CONTRIBUTION",
        status="FLAGGED",
        description=f"First-time enrollment large contribution to {group3.name}",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    )
    db.add(tx3)
    db.commit()
    db.refresh(tx3)

    c_first = Contribution(
        member_id=u_first.id,
        group_id=group3.id,
        amount=25000.0,
        payment_method="Bank Transfer (Demo)",
        transaction_ref=tx3_ref,
        status="PENDING",
        notes="Collateral installment upfront",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    )
    db.add(c_first)
    db.commit()

    alert3 = RiskAlert(
        transaction_id=tx3.id,
        member_id=u_first.id,
        member_name=u_first.full_name,
        group_id=group3.id,
        group_name=group3.name,
        amount=25000.0,
        risk_level="HIGH",
        anomaly_score=0.92,
        reasons_json=json.dumps([
            {"indicator": "+", "type": "FLAG", "message": "Transaction amount (₹25,000.00) is 5.0x the baseline pool rule (₹5,000.00)."},
            {"indicator": "+", "type": "INFO", "message": "First recorded transaction for this member with zero prior baseline history."},
            {"indicator": "-", "type": "POSITIVE", "message": "Transaction originated via verified bank transfer rail."}
        ]),
        recommended_action="Administrator manual verification required before ledger entry",
        status="PENDING_REVIEW"
    )
    db.add(alert3)

    # 9. Seed Audit Logs
    print("[+] Seeding Initial Audit Trail...")
    audit_samples = [
        ("Rajesh Sharma (Admin)", "ADMIN", "SYSTEM_INITIALIZATION", "SYSTEM", "1", "SaveCircle FinTech platform initialized with secure audit subsystem."),
        ("Rajesh Sharma (Admin)", "ADMIN", "CREATE_GROUP", "GROUP", str(group1.id), f"Admin created savings group '{group1.name}' (Monthly ₹2,000)."),
        ("Rajesh Sharma (Admin)", "ADMIN", "CREATE_GROUP", "GROUP", str(group2.id), f"Admin created savings group '{group2.name}' (Monthly ₹1,500)."),
        ("Rajesh Sharma (Admin)", "ADMIN", "CREATE_GROUP", "GROUP", str(group3.id), f"Admin created savings group '{group3.name}' (Monthly ₹5,000)."),
        ("SYSTEM_AUTOMATION", "SYSTEM", "TRANSACTION_FLAGGED_BY_AI", "RISK_ALERT", str(tx1.id), f"AI Anomaly Engine flagged High-Risk pattern on transaction {tx1_ref} (₹20,000.00)."),
        ("SYSTEM_AUTOMATION", "SYSTEM", "TRANSACTION_FLAGGED_BY_AI", "RISK_ALERT", str(tx2.id), f"AI Anomaly Engine flagged Medium-Risk velocity spike on transaction {tx2_ref} (₹6,000.00)."),
        ("SYSTEM_AUTOMATION", "SYSTEM", "TRANSACTION_FLAGGED_BY_AI", "RISK_ALERT", str(tx3.id), f"AI Anomaly Engine flagged High-Risk baseline outlier on transaction {tx3_ref} (₹25,000.00)."),
    ]

    for actor_name, role, action, e_type, e_id, desc in audit_samples:
        db.add(AuditLog(
            actor_name=actor_name,
            actor_role=role,
            action=action,
            entity_type=e_type,
            entity_id=e_id,
            description=desc,
            ip_address="127.0.0.1",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=10)
        ))

    db.commit()
    db.close()
    print("[✓] SaveCircle Database successfully seeded with 3 groups, 22 users, 40+ transactions, verified receipts, and 3 flagged AI anomalies!")

if __name__ == "__main__":
    seed_database()
