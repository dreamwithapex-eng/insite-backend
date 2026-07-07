# app/rules.py
from datetime import datetime

RULESET_VERSION = "0.2.0"


def create_constraint(category, status, confidence, evidence, next_step):
    return {
        "category": category,
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "next_step": next_step,
    }


def explanations_for_tier(tier):
    """
    Canonical, underwriting-safe tier explanations.
    Intentionally brief, city-agnostic, and non-binding.
    """
    if tier == "green":
        return [
            "Parcel shows a favorable early feasibility profile based on available data.",
            "No major disqualifying constraints detected at pre-feasibility stage.",
        ]
    elif tier == "amber":
        return [
            "One or more feasibility risk factors were identified; further diligence is recommended.",
        ]
    elif tier == "red":
        return [
            "Parcel fails one or more baseline feasibility checks based on available data.",
        ]
    return []


def analyze(parcel):
    """
    iNSITE Core rules entrypoint.
    Returns score, tier, flags, explanations, and FSS 2.0 constraint objects.
    """
    flags = []
    explanations = []
    constraints = []

    zoning = (parcel.get("zoning") or "").strip()
    zoning_normalized = zoning.lower()
    lot_sqft = parcel.get("lot_sqft")

    # Zoning signal
    if not zoning_normalized:
        flags.append("MISSING_ZONING")
        explanations.append("Zoning information is missing; analysis confidence is reduced.")

        constraints.append(
            create_constraint(
                "Zoning",
                "Review Needed",
                "Low",
                "No zoning information detected in parcel record.",
                "Verify zoning classification with the local authority before design or acquisition commitment.",
            )
        )
    else:
        constraints.append(
            create_constraint(
                "Zoning",
                "Available",
                "Medium",
                f"Parcel record contains zoning designation: {zoning}.",
                "Confirm permitted use and applicable zoning interpretation before design or acquisition commitment.",
            )
        )

    # Parcel dimensions / lot size signal
    if lot_sqft is None or str(lot_sqft).strip() == "":
        flags.append("MISSING_LOT_SIZE")
        explanations.append("Lot size is missing; analysis confidence is reduced.")

        constraints.append(
            create_constraint(
                "Parcel Dimensions",
                "Review Needed",
                "Low",
                "Lot size information is missing from parcel record.",
                "Confirm lot area and applicable dimensional standards during diligence.",
            )
        )
    else:
        try:
            lot_sqft_val = float(lot_sqft)

            if lot_sqft_val < 2500:
                flags.append("VERY_SMALL_LOT")
                explanations.append("Lot size is very small; feasibility may be constrained.")

                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Constraint Detected",
                        "High",
                        f"Parcel lot size is {lot_sqft_val:,.0f} square feet, below the baseline screening threshold of 2,500 square feet.",
                        "Review minimum lot size, setbacks, frontage, and buildable area requirements before advancing.",
                    )
                )
            else:
                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Low Friction",
                        "High",
                        f"Parcel lot size is {lot_sqft_val:,.0f} square feet and passes the baseline lot-size screening threshold.",
                        "Confirm detailed dimensional standards during formal diligence.",
                    )
                )

        except (TypeError, ValueError):
            flags.append("INVALID_LOT_SIZE")
            explanations.append("Lot size could not be parsed as a number.")

            constraints.append(
                create_constraint(
                    "Parcel Dimensions",
                    "Review Needed",
                    "Low",
                    "Lot size value could not be parsed from parcel record.",
                    "Confirm parcel area from source records before relying on feasibility results.",
                )
            )

    # Future constraint layers — intentionally conservative placeholders
    constraints.append(
        create_constraint(
            "Utilities",
            "Data Pending",
            "Low",
            "Utility service datasets are not connected in this ruleset version.",
            "Verify water, sewer, electric, and other service availability with the appropriate provider.",
        )
    )

    constraints.append(
        create_constraint(
            "Environmental",
            "Data Pending",
            "Low",
            "Environmental constraint datasets are not connected in this ruleset version.",
            "Complete floodplain, environmental, and site-condition verification during diligence.",
        )
    )

    constraints.append(
        create_constraint(
            "Infrastructure Access",
            "Data Pending",
            "Low",
            "Infrastructure and access datasets are not connected in this ruleset version.",
            "Verify road access, frontage, and infrastructure readiness before committing resources.",
        )
    )

    # Simple scoring placeholder (0–100)
    score = 80
    if "MISSING_ZONING" in flags:
        score -= 25
    if "MISSING_LOT_SIZE" in flags or "INVALID_LOT_SIZE" in flags:
        score -= 20
    if "VERY_SMALL_LOT" in flags:
        score -= 10

    score = max(0, min(100, score))

    # Canonical tiers: Green / Amber / Red
    tier = "green" if score >= 70 else ("amber" if score >= 45 else "red")

    # User-facing signal
    if tier == "green":
        signal = "Proceed with Verification"
    elif tier == "amber":
        signal = "Review Before Advancing"
    else:
        signal = "High Constraint"

    explanations = explanations + explanations_for_tier(tier)

    return {
        "score": score,
        "tier": tier,
        "signal": signal,
        "flags": flags,
        "explanations": explanations,
        "constraints": constraints,
        "ruleset_version": RULESET_VERSION,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }