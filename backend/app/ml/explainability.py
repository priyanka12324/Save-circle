from typing import Dict, Any, List

def format_explainability_summary(analysis: Dict[str, Any]) -> str:
    """
    Format a concise, respectful, non-accusatory summary of the AI analysis.
    Adheres strictly to the PRD guideline:
    Never display 'User is fraudulent'; display 'Unusual transaction pattern detected'.
    """
    level = analysis.get("risk_level", "LOW")
    if level in ["HIGH", "MEDIUM"]:
        prefix = "UNUSUAL TRANSACTION PATTERN DETECTED"
    else:
        prefix = "STANDARD TRANSACTION PATTERN"
    
    reasons_list = analysis.get("reasons", [])
    bullets = "\n".join([f"{r.get('indicator', '*')} {r.get('message', '')}" for r in reasons_list])
    
    return f"{prefix} (Risk Level: {level})\n{bullets}\nRecommended Action: {analysis.get('recommended_action', 'Review')}"
