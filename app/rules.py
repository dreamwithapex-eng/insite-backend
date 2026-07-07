# app/rules.py
from datetime import datetime

RULESET_VERSION = "0.4.0"


def create_constraint(category, status, confidence, evidence, next_step):
    return {
        "category": category,
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "next_step": next_step,
    }


def interpret_zoning(zoning):
    """
    Converts raw zoning labels into conservative development context signals.
    This does NOT determine entitlement approval.
    """
    zoning_text = zoning.lower()

    if any(term in zoning_text for term in [
        "single-family",
        "single family",
        "residential single",
        "r-6"
    ]):
        return {
            "category": "Residential",
            "intensity": "Low Density",
            "pathway": "Single-family residential pathway detected",
        }

    if any(term in zoning_text for term in [
        "medium density residential",
        "residential urban",
        "ru-1"
    ]):
        return {
            "category": "Residential",
            "intensity": "Medium Density",
            "pathway": "Urban residential pathway detected",
        }

    if "high density residential" in zoning_text:
        return {
            "category": "Residential",
            "intensity": "High Density",
            "pathway": "Higher-density residential pathway detected",
        }

    if "commercial" in zoning_text:
        return {
            "category": "Commercial",
            "intensity": "Varies",
            "pathway": "Commercial development pathway detected",
        }

    if "industrial" in zoning_text:
        return {
            "category": "Industrial",
            "intensity": "Varies",
            "pathway": "Industrial development pathway detected",
        }

    return {
        "category": "Unknown",
        "intensity": "Unknown",
        "pathway": "Zoning classification requires additional review",
    }


def explanations_for_tier(tier):
    """
    Canonical, underwriting-safe tier explanations.
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
    Returns score, tier, signal, constraints, and evidence.
    """
    flags = []
    explanations = []
    constraints = []

    zoning = (parcel.get("zoning") or "").strip()
    zoning_normalized = zoning.lower()
    lot_sqft = parcel.get("lot_sqft")

    # Zoning Intelligence
    if not zoning_normalized:
        flags.append("MISSING_ZONING")
        explanations.append(
            "Zoning information is missing; analysis confidence is reduced."
        )

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
        zoning_result = interpret_zoning(zoning)

        constraints.append(
            create_constraint(
                "Zoning",
                f"{zoning_result['category']} Pathway Detected",
                "High",
                f"Parcel is classified as {zoning}. iNSITE identified a {zoning_result['intensity']} {zoning_result['category']} development context.",
                "Verify permitted uses, overlays, dimensional standards, and entitlement requirements before commitment.",
            )
        )


    # Parcel Dimensions
    if lot_sqft is None or str(lot_sqft).strip() == "":
        flags.append("MISSING_LOT_SIZE")

        constraints.append(
            create_constraint(
                "Parcel Dimensions",
                "Review Needed",
                "Low",
                "Lot size information is missing from parcel record.",
                "Confirm lot area and dimensional standards during diligence.",
            )
        )

    else:
        try:
            lot_sqft_val = float(lot_sqft)

            if lot_sqft_val < 2500:
                flags.append("VERY_SMALL_LOT")

                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Constraint Detected",
                        "High",
                        f"Parcel lot size is {lot_sqft_val:,.0f} square feet, below baseline screening threshold.",
                        "Review minimum lot size, setbacks, frontage, and buildable area requirements before advancing.",
                    )
                )

            else:
                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Low Friction",
                        "High",
                        f"Parcel lot size is {lot_sqft_val:,.0f} square feet and passes baseline screening threshold.",
                        "Confirm detailed dimensional standards during formal diligence.",
                    )
                )

        except (TypeError, ValueError):
            flags.append("INVALID_LOT_SIZE")

            constraints.append(
                create_constraint(
                    "Parcel Dimensions",
                    "Review Needed",
                    "Low",
                    "Lot size could not be parsed.",
                    "Confirm parcel area from source records.",
                )
            )


    # Future Layers
    constraints.append(
        create_constraint(
            "Utilities",
            "Data Pending",
            "Low",
            "Utility service datasets are not connected in this ruleset version.",
            "Verify water, sewer, electric, and service availability.",
        )
    )

    constraints.append(
        create_constraint(
            "Environmental",
            "Data Pending",
            "Low",
            "Environmental datasets are not connected in this ruleset version.",
            "Complete floodplain and environmental verification.",
        )
    )

    constraints.append(
        create_constraint(
            "Infrastructure Access",
            "Data Pending",
            "Low",
            "Infrastructure datasets are not connected in this ruleset version.",
            "Verify access, frontage, and infrastructure readiness.",
        )
    )


    # Score
    score = 80

    if "MISSING_ZONING" in flags:
        score -= 25

    if "MISSING_LOT_SIZE" in flags or "INVALID_LOT_SIZE" in flags:
        score -= 20

    if "VERY_SMALL_LOT" in flags:
        score -= 10

    score = max(0, min(100, score))


    # Tier
    tier = "green" if score >= 75 else ("amber" if score >= 45 else "red")


    # Signal
    if tier == "green":
        signal = "Proceed with Verification"

    elif tier == "amber":
        signal = "Review Before Advancing"

    else:
        signal = "High Constraint"


    explanations += explanations_for_tier(tier)


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