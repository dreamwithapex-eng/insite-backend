# app/data.py
from typing import Any, Dict, Optional
import csv
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_parcel_from_csv(city, parcel_id):
    """
    Looks for a file at: data/<city>/parcels.csv
    Must contain a column named 'parcel_id' (exact name).
    Returns the row as a dict if found, else None.
    """
    city = city.strip().lower()
    parcel_id = str(parcel_id).strip()

    path = os.path.join(DATA_DIR, city, "parcels.csv")
    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_id = str(row.get("parcel_id", "")).strip()
            req_id = str(parcel_id).strip()

            # --- Harden parcel_id matching ---
            try:
                pass_match = float(csv_id) == float(req_id)
            except Exception:
                pass_match = csv_id == req_id

            if pass_match:
                normalized = dict(row)

                # --- Canonical field mapping (v0.1) ---
                # Zoning
                if "zoning" not in normalized or not normalized.get("zoning"):
                    if "Zoning" in normalized and normalized.get("Zoning"):
                        normalized["zoning"] = normalized.get("Zoning")

                # Lot size (support Nashville acres -> lot_sqft)
                if ("lot_sqft" not in normalized) or (normalized.get("lot_sqft") in ("", None)):
                    acres_val = normalized.get("Acres") or normalized.get("acres")
                    if acres_val not in ("", None):
                        try:
                            normalized["lot_sqft"] = float(acres_val) * 43560
                        except Exception:
                            pass

                # Ensure lot_sqft is None (not "") if blank
                if "lot_sqft" in normalized and normalized["lot_sqft"] == "":
                    normalized["lot_sqft"] = None

                return normalized

    return None

