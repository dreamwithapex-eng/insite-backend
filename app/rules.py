# app/rules.py
from typing import Any, Dict, List
from datetime import datetime

RULESET_VERSION = "0.1.0"

def analyze(parcel: Dict[str, Any]) -> Dict[str, Any]:
    """
    This is your single 'brain entrypoint'.
    Later, you replace the placeholder logic with your real iNSITE rules engine.
    """
    flags: List[str] = []
    explanations: List[str] = []

    # ---- Placeholder checks (replace with your real logic) ----
    zoning = (parcel.get("zoning") or "").strip().lower()
    lot_sqft = parcel.get("lot_sqft")

    if not zoning:
        flags.append("MISSING_ZONING")
        explanations.append("Zoning is missing; analysis confidence is reduced.")

    if lot_sqft is None:
        flags.append("MISSING_LOT_SIZE")
        explanations.append("Lot size (lot_sqft) is missing; analysis confidence is reduced.")
    else:
        try:
            lot_sqft_val = float(lot_sqft)
            if lot_sqft_val < 2500:
                flags.append("VERY_SMALL_LOT")
                explanations.append("Lot size is very small; feasibility may be constrained.")
        except Exception:
            flags.append("INVALID_LOT_SIZE")
            explanations.append("Lot size could not be parsed as a number.")

    # Simple scoring placeholder (0–100)
    score = 80
    if "MISSING_ZONING" in flags:
        score -= 25
    if "MISSING_LOT_SIZE" in flags or "INVALID_LOT_SIZE" in flags:
        score -= 20
    if "VERY_SMALL_LOT" in flags:
        score -= 10
    score = max(0, min(100, score))

    return {
        "score": score,
        "tier": "green" if score >= 70 else ("yellow" if score >= 45 else "red"),
        "flags": flags,
        "explanations": explanations,
        "ruleset_version": RULESET_VERSION,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }
