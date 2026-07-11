# app/rules.py
from datetime import datetime

RULESET_VERSION = "0.7.0"


def create_constraint(category, status, confidence, evidence, next_step):
    return {
        "category": category,
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "next_step": next_step,
    }


def interpret_zoning(zoning):
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
        }

    if "high density residential" in zoning_text:
        return {
            "category": "Residential",
            "intensity": "High Density",
        }

    if "commercial" in zoning_text:
        return {
            "category": "Commercial",
            "intensity": "Varies",
        }

    if "industrial" in zoning_text:
        return {
            "category": "Industrial",
            "intensity": "Varies",
        }

    return {
        "category": "Unknown",
        "intensity": "Unknown",
    }


def explanations_for_tier(tier):
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
    flags = []
    explanations = []
    constraints = []

    zoning = (parcel.get("zoning") or "").strip()
    zoning_normalized = zoning.lower()
    lot_sqft = parcel.get("lot_sqft")
    flood_zone = (parcel.get("flood_zone") or "").strip().upper()

    road_access = (parcel.get("road_access") or "").strip().lower()
    road_frontage = (parcel.get("road_frontage") or "").strip().lower()
    street_class = (parcel.get("street_class") or "").strip().lower()

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
                f"Flood-zone value '{flood_zone}' is not recognized by the current ruleset.",
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

    # Infrastructure Access Intelligence
    infrastructure_fields_missing = not any(
        [road_access, road_frontage, street_class]
    )

    if infrastructure_fields_missing:
        constraints.append(
            create_constraint(
                "Infrastructure Access",
                "Data Pending",
                "Low",
                "No road-access, frontage, or street-class information is currently available for this parcel.",
                "Verify legal access, public frontage, roadway classification, and ingress or egress requirements before advancing.",
            )
        )

    elif road_access in {"no", "none", "not confirmed", "unconfirmed"} or road_frontage in {
        "no",
        "none",
    }:
        flags.append("ACCESS_CONSTRAINT")
        explanations.append(
            "Available infrastructure data indicates a potential access or frontage constraint."
        )

        constraints.append(
            create_constraint(
                "Infrastructure Access",
                "Access Constraint Detected",
                "High",
                (
                    f"Road access is recorded as '{road_access or 'unknown'}' and "
                    f"road frontage is recorded as '{road_frontage or 'unknown'}'."
                ),
                "Confirm legal access, public right-of-way frontage, curb-cut eligibility, and ingress or egress requirements before advancing.",
            )
        )

    elif road_access in {"review", "unknown", "pending"} or road_frontage in {
        "review",
        "unknown",
        "pending",
    }:
        flags.append("INFRASTRUCTURE_REVIEW")
        explanations.append(
            "Infrastructure access information requires focused verification."
        )

        constraints.append(
            create_constraint(
                "Infrastructure Access",
                "Infrastructure Review Recommended",
                "Medium",
                (
                    f"Road access is recorded as '{road_access or 'unknown'}', "
                    f"road frontage as '{road_frontage or 'unknown'}', and "
                    f"street class as '{street_class or 'unknown'}'."
                ),
                "Verify public access, frontage, roadway classification, and ingress or egress conditions before advancing.",
            )
        )

    elif road_access in {"confirmed", "yes"} and road_frontage == "yes":
        street_description = street_class if street_class else "unspecified"

        constraints.append(
            create_constraint(
                "Infrastructure Access",
                "Low Infrastructure Friction",
                "Medium",
                (
                    "Available parcel data indicates confirmed road access and public frontage. "
                    f"The recorded street classification is '{street_description}'."
                ),
                "Confirm final curb-cut, ingress, egress, and transportation requirements during formal diligence.",
            )
        )

    else:
        flags.append("INFRASTRUCTURE_REVIEW")

        constraints.append(
            create_constraint(
                "Infrastructure Access",
                "Infrastructure Review Recommended",
                "Low",
                (
                    f"Road access is recorded as '{road_access or 'unknown'}', "
                    f"road frontage as '{road_frontage or 'unknown'}', and "
                    f"street class as '{street_class or 'unknown'}'."
                ),
                "Verify legal access, frontage, roadway classification, and ingress or egress requirements before advancing.",
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

    if "INFRASTRUCTURE_REVIEW" in flags:
        score -= 5

    if "ACCESS_CONSTRAINT" in flags:
        score -= 10

    score = max(0, min(100, score))

    tier = "green" if score >= 75 else ("amber" if score >= 45 else "red")

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