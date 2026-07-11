# app/data.py
from typing import Any, Dict, Optional
import csv
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_parcel_from_csv(city, parcel_id):
    """
    Loads a parcel from data/<city>/parcels.csv.

    The CSV must contain a parcel_id column.
    All CSV fields are returned, including optional environmental
    and infrastructure fields.
    """
    city = str(city).strip().lower()
    parcel_id = str(parcel_id).strip()

    path = os.path.join(DATA_DIR, city, "parcels.csv")

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            csv_id = str(row.get("parcel_id", "")).strip()

            # Preserve support for parcel IDs entered without leading zeros.
            try:
                pass_match = float(csv_id) == float(parcel_id)
            except (TypeError, ValueError):
                pass_match = csv_id == parcel_id

            if not pass_match:
                continue

            # Keep every CSV column.
            normalized = {
                str(key).strip(): value
                for key, value in row.items()
                if key is not None
            }

            # Zoning normalization.
            if not normalized.get("zoning"):
                zoning_value = normalized.get("Zoning")
                if zoning_value:
                    normalized["zoning"] = zoning_value

            if normalized.get("zoning") is not None:
                normalized["zoning"] = str(
                    normalized["zoning"]
                ).strip()

            # Lot-size normalization, including Nashville acres fallback.
            if normalized.get("lot_sqft") in ("", None):
                acres_value = (
                    normalized.get("Acres")
                    or normalized.get("acres")
                )

                if acres_value not in ("", None):
                    try:
                        normalized["lot_sqft"] = (
                            float(acres_value) * 43560
                        )
                    except (TypeError, ValueError):
                        pass

            if normalized.get("lot_sqft") == "":
                normalized["lot_sqft"] = None

            # Optional environmental and infrastructure fields.
            optional_fields = [
                "flood_zone",
                "road_access",
                "road_frontage",
                "street_class",
            ]

            for field in optional_fields:
                value = normalized.get(field)

                if value is None:
                    normalized[field] = ""
                else:
                    normalized[field] = str(value).strip()

            return normalized

    return None