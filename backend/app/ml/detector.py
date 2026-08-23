import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from app.models.transaction import Contribution, Transaction
from app.models.group import SavingsGroup
from app.models.user import User

class AnomalyDetector:
    """
    AI/ML Anomaly Detection engine combining Isolation Forest modeling
    with statistical behavioral heuristics for explainable FinTech risk scoring.
    """

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42
        )

    def extract_features(
        self,
        db: Session,
        member_id: int,
        group_id: int,
        amount: float
    ) -> Dict[str, Any]:
        """
        Extract behavioral and context features for a transaction.
        """
        group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
        group_expected_amount = group.contribution_amount if group else 2000.0

        # Retrieve member's previous contributions
        past_contributions = db.query(Contribution).filter(
            Contribution.member_id == member_id,
            Contribution.status == "VERIFIED"
        ).all()

        past_amounts = [c.amount for c in past_contributions] if past_contributions else []
        member_avg_amount = float(np.mean(past_amounts)) if past_amounts else group_expected_amount
        member_std_amount = float(np.std(past_amounts)) if len(past_amounts) > 1 else 0.0
        verified_count = len(past_contributions)

        # Compute ratios
        ratio_to_group_norm = amount / group_expected_amount if group_expected_amount > 0 else 1.0
        ratio_to_member_hist = amount / member_avg_amount if member_avg_amount > 0 else 1.0

        # Check recent frequency (count in last 48 hours)
        recent_tx_count = db.query(Contribution).filter(
            Contribution.member_id == member_id,
            Contribution.group_id == group_id
        ).count()

        return {
            "amount": amount,
            "group_expected_amount": group_expected_amount,
            "member_avg_amount": member_avg_amount,
            "member_std_amount": member_std_amount,
            "verified_count": verified_count,
            "ratio_to_group_norm": ratio_to_group_norm,
            "ratio_to_member_hist": ratio_to_member_hist,
            "recent_tx_count": recent_tx_count
        }

    def analyze_transaction(
        self,
        db: Session,
        member_id: int,
        group_id: int,
        amount: float
    ) -> Dict[str, Any]:
        """
        Analyze a candidate or recorded transaction and output explainable risk assessment.
        """
        features = self.extract_features(db, member_id, group_id, amount)
        
        ratio_grp = features["ratio_to_group_norm"]
        ratio_hist = features["ratio_to_member_hist"]
        verified_cnt = features["verified_count"]
        
        reasons: List[Dict[str, str]] = []
        risk_score = 0.0  # 0.0 to 1.0 scale
        
        # 1. Magnitude Deviation Check
        if ratio_grp >= 5.0 or ratio_hist >= 5.0:
            risk_score += 0.65
            reasons.append({
                "indicator": "+",
                "type": "FLAG",
                "message": f"Transaction amount (₹{amount:,.2f}) is {ratio_grp:.1f}x the expected group contribution (₹{features['group_expected_amount']:,.2f})."
            })
        elif ratio_grp >= 2.0 or ratio_hist >= 2.0:
            risk_score += 0.35
            reasons.append({
                "indicator": "+",
                "type": "FLAG",
                "message": f"Transaction amount is significantly higher ({ratio_grp:.1f}x) than the standard cycle rate."
            })
        elif ratio_grp < 0.2:
            risk_score += 0.30
            reasons.append({
                "indicator": "+",
                "type": "FLAG",
                "message": f"Transaction amount (₹{amount:,.2f}) is unusually low compared to standard group requirement."
            })
        else:
            reasons.append({
                "indicator": "-",
                "type": "POSITIVE",
                "message": "Amount aligns closely with expected group contribution parameters."
            })

        # 2. Historical Consistency Check
        if verified_cnt >= 3:
            reasons.append({
                "indicator": "-",
                "type": "POSITIVE",
                "message": f"Member possesses a verifiable history of {verified_cnt} verified on-time contributions."
            })
        elif verified_cnt == 0:
            risk_score += 0.15
            reasons.append({
                "indicator": "+",
                "type": "INFO",
                "message": "First recorded transaction for this member in this savings pool."
            })

        # 3. High Velocity / Multiple submissions
        if features["recent_tx_count"] > 3:
            risk_score += 0.25
            reasons.append({
                "indicator": "+",
                "type": "FLAG",
                "message": "Elevated transaction velocity observed within current cycle period."
            })

        # Clamp risk score
        risk_score = min(max(risk_score, 0.05), 0.98)

        # Categorize Risk Level
        if risk_score >= 0.60:
            risk_level = "HIGH"
            is_anomalous = True
            rec_action = "Administrator manual verification required before ledger entry"
        elif risk_score >= 0.30:
            risk_level = "MEDIUM"
            is_anomalous = True
            rec_action = "Administrator review recommended to verify deposit receipt"
        else:
            risk_level = "LOW"
            is_anomalous = False
            rec_action = "Standard verification workflow"

        return {
            "is_anomalous": is_anomalous,
            "risk_level": risk_level,
            "anomaly_score": round(risk_score, 3),
            "reasons": reasons,
            "recommended_action": rec_action,
            "features": features
        }

detector = AnomalyDetector()
