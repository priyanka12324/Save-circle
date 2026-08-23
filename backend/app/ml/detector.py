import datetime
from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.config import settings
from app.models.group import SavingsGroup
from app.models.transaction import Contribution


class AnomalyDetector:
    """Hybrid explainable risk engine with statistical and Isolation Forest signals."""

    def __init__(self, contamination: float | None = None):
        self.contamination = contamination or settings.AI_CONTAMINATION_RATE

    def extract_features(self, db: Session, member_id: int, group_id: int, amount: float) -> Dict[str, Any]:
        group = db.query(SavingsGroup).filter(SavingsGroup.id == group_id).first()
        expected = float(group.contribution_amount) if group else 2000.0

        history = db.query(Contribution).filter(
            Contribution.member_id == member_id,
            Contribution.group_id == group_id,
            Contribution.status == "VERIFIED",
        ).all()
        amounts = [float(item.amount) for item in history]
        average = float(np.mean(amounts)) if amounts else expected
        std = float(np.std(amounts)) if len(amounts) > 1 else 0.0
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=48)
        recent_count = db.query(Contribution).filter(
            Contribution.member_id == member_id,
            Contribution.group_id == group_id,
            Contribution.created_at >= cutoff,
        ).count()

        return {
            "amount": amount,
            "group_expected_amount": expected,
            "member_avg_amount": average,
            "member_std_amount": std,
            "verified_count": len(history),
            "ratio_to_group_norm": amount / expected if expected else 1.0,
            "ratio_to_member_hist": amount / average if average else 1.0,
            "recent_tx_count_48h": recent_count,
            "historical_amounts": amounts,
        }

    def _ml_signal(self, historical_amounts: List[float], candidate: float) -> tuple[bool, float] | None:
        """Return an Isolation Forest signal only when enough history exists."""
        if len(historical_amounts) < 10:
            return None
        training = np.array(historical_amounts, dtype=float).reshape(-1, 1)
        model = IsolationForest(
            n_estimators=100,
            contamination=min(max(self.contamination, 0.01), 0.49),
            random_state=42,
        )
        model.fit(training)
        sample = np.array([[candidate]], dtype=float)
        is_outlier = bool(model.predict(sample)[0] == -1)
        # decision_function is lower for more unusual observations.
        raw = float(model.decision_function(sample)[0])
        confidence = float(np.clip(0.5 - raw, 0.0, 1.0))
        return is_outlier, confidence

    def analyze_transaction(self, db: Session, member_id: int, group_id: int, amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")

        features = self.extract_features(db, member_id, group_id, amount)
        ratio_group = features["ratio_to_group_norm"]
        ratio_history = features["ratio_to_member_hist"]
        verified_count = features["verified_count"]
        reasons: List[Dict[str, str]] = []
        risk_score = 0.0

        if ratio_group >= 5.0 or ratio_history >= 5.0:
            risk_score += 0.65
            reasons.append({"indicator": "+", "type": "FLAG", "message": f"Amount is {ratio_group:.1f}x the expected group contribution."})
        elif ratio_group >= 2.0 or ratio_history >= 2.0:
            risk_score += 0.35
            reasons.append({"indicator": "+", "type": "FLAG", "message": f"Amount is {ratio_group:.1f}x the standard cycle rate."})
        elif ratio_group < 0.2:
            risk_score += 0.30
            reasons.append({"indicator": "+", "type": "FLAG", "message": "Amount is unusually low compared with the group requirement."})
        else:
            reasons.append({"indicator": "-", "type": "POSITIVE", "message": "Amount aligns with the expected contribution range."})

        if verified_count >= 3:
            reasons.append({"indicator": "-", "type": "POSITIVE", "message": f"Member has {verified_count} verified contributions in this group."})
        elif verified_count == 0:
            risk_score += 0.15
            reasons.append({"indicator": "+", "type": "INFO", "message": "This is the member's first recorded contribution in the group."})

        if features["recent_tx_count_48h"] > 3:
            risk_score += 0.25
            reasons.append({"indicator": "+", "type": "FLAG", "message": "More than three submissions were recorded in the last 48 hours."})

        ml_signal = self._ml_signal(features.pop("historical_amounts"), amount)
        if ml_signal:
            is_outlier, confidence = ml_signal
            if is_outlier:
                risk_score += 0.20
                reasons.append({"indicator": "+", "type": "ML_SIGNAL", "message": "Isolation Forest marked the amount as unusual against sufficient member history."})
            else:
                reasons.append({"indicator": "-", "type": "ML_SIGNAL", "message": "Isolation Forest found the amount consistent with member history."})
            features["ml_confidence"] = round(confidence, 3)
            features["ml_model_used"] = True
        else:
            features["ml_model_used"] = False
            reasons.append({"indicator": "-", "type": "INFO", "message": "Rule-based review used because fewer than 10 historical samples are available."})

        risk_score = min(max(risk_score, 0.05), 0.98)
        if risk_score >= 0.60:
            level, anomalous, action = "HIGH", True, "Administrator manual verification required before ledger entry"
        elif risk_score >= 0.30:
            level, anomalous, action = "MEDIUM", True, "Administrator review recommended to verify the deposit receipt"
        else:
            level, anomalous, action = "LOW", False, "Standard verification workflow"

        return {
            "is_anomalous": anomalous,
            "risk_level": level,
            "anomaly_score": round(risk_score, 3),
            "reasons": reasons,
            "recommended_action": action,
            "features": features,
        }


detector = AnomalyDetector()
