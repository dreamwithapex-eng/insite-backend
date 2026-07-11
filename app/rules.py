# app/rules.py
from datetime import datetime

RULESET_VERSION = "0.6.0"


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
    This does not determine entitlement approval.
    """
    zoning_text = zoning.lower()

    if any(
        term in zoning_text
        for term in [
            "single-family",
            "single family",
            "residential single",
            "r-6",
        ]
    ):
        return {
            "category": "Residential",
            "intensity": "Low Density",
            "pathway": "Single-family residential pathway detected",
        }

    if any(
        term in zoning_text
        for term in [
            "medium density residential",
            "residential urban",
            "ru-1",
        ]
    ):
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

    if tier == "amber":
        return [
            "One or more feasibility risk factors were identified; further diligence is recommended.",
        ]

    if tier == "red":
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

    flood_zone = (parcel.get("flood_zone") or "").strip().upper()

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
                (
                    f"Parcel is classified as {zoning}. "
                    f"iNSITE identified a {zoning_result['intensity']} "
                    f"{zoning_result['category']} development context."
                ),
                "Verify permitted uses, overlays, dimensional standards, and entitlement requirements before commitment.",
            )
        )

    # Parcel Dimensions
    if lot_sqft is None or str(lot_sqft).strip() == "":
        flags.append("MISSING_LOT_SIZE")
        explanations.append(
            "Lot size information is missing; analysis confidence is reduced."
        )

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
                explanations.append(
                    "Parcel lot size is below the baseline screening threshold."
                )

                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Constraint Detected",
                        "High",
                        (
                            f"Parcel lot size is {lot_sqft_val:,.0f} square feet, "
                            "below the baseline screening threshold of 2,500 square feet."
                        ),
                        "Review minimum lot size, setbacks, frontage, and buildable area requirements before advancing.",
                    )
                )
            else:
                constraints.append(
                    create_constraint(
                        "Parcel Dimensions",
                        "Low Friction",
                        "High",
                        (
                            f"Parcel lot size is {lot_sqft_val:,.0f} square feet "
                            "and passes the baseline lot-size screening threshold."
                        ),
                        "Confirm detailed dimensional standards during formal diligence.",
                    )
                )

        except (TypeError, ValueError):
            flags.append("INVALID_LOT_SIZE")
            explanations.append(
                "Lot size could not be parsed from the parcel record."
            )

            constraints.append(
                create_constraint(
                    "Parcel Dimensions",
                    "Review Needed",
                    "Low",
                    "Lot size could not be parsed from the parcel record.",
                    "Confirm parcel area from authoritative source records.",
                )
            )

    # Environmental Intelligence
    if not flood_zone:
        constraints.append(
            create_constraint(
                "Environmental",
                "Data Pending",
                "Low",
                "No floodplain information is currently available for this parcel.",
                "Complete floodplain and environmental verification before advancing.",
            )
        )

    elif flood_zone in {"X", "X500"}:
        constraints.append(
            create_constraint(
                "Environmental",
                "Low Environmental Friction",
                "Medium",
                (
                    f"Available records indicate Flood Zone {flood_zone}. "
                    "No special flood-hazard signal was detected from the available environmental data."
                ),
                "Continue standard environmental diligence appropriate to the project.",
            )
        )

    elif flood_zone in {"A", "AE", "AH", "AO", "V", "VE"}:
        flags.append("FLOOD_REVIEW")
        explanations.append(
            f"Flood Zone {flood_zone} indicates that focused floodplain review is recommended."
        )

        constraints.append(
            create_constraint(
                "Environmental",
                "Environmental Review Recommended",
                "High",
                (
                    f"Available records indicate FEMA Flood Zone {flood_zone}, "
                    "which may affect development requirements."
                ),
                "Verify floodplain status, insurance requirements, elevation requirements, and applicable development restrictions before advancing.",
            )
        )

    else:
        flags.append("UNRECOGNIZED_FLOOD_ZONE")
        explanations.append(
            "The available flood-zone value requires manual verification."
        )

        constraints.append(
            create_constraint(
                "Environmental",
                "Environmental Review Needed",
                "Low",
                (
                    f"Flood-zone value '{flood_zone}' is not recognized by "
                    "the current ruleset."
                ),
                "Verify environmental conditions using authoritative local and FEMA sources.",
            )
        )

    # Utilities Placeholder
    constraints.append(
        create_constraint(
            "Utilities",
            "Data Pending",
            "Low",
            "Utility service datasets are not connected in this ruleset version.",
            "Verify water, sewer, electric, and other service availability with the appropriate provider.",
        )
    )

    # Infrastructure Access Placeholder
    constraints.append(
        create_constraint(
            "Infrastructure Access",
            "Data Pending",
            "Low",
            "Infrastructure and access datasets are not connected in this ruleset version.",
            "Verify road access, frontage, and infrastructure readiness before committing resources.",
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

    if "FLOOD_REVIEW" in flags:
        score -= 5

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