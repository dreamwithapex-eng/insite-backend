# app/data.py
from typing import Any, Dict, Optional
import csv
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_parcel_from_csv(city: str, parcel_id: str) -> Optional[Dict[str, Any]]:
    """
    Looks for a file at: data/<city>.csv
    Must contain a column named 'parcel_id' (exact name).
    Returns the row as a dict if found, else None.
    """
    city = city.strip().lower()
    path = os.path.join(DATA_DIR, f"{city}.csv")
    if not os.path.exists(path):
        return None

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("parcel_id", "")).strip() == str(parcel_id).strip():
                # Normalize a couple fields for the rules stub
                # (You will replace these mappings with your real schema later.)
                normalized = dict(row)
                if "lot_sqft" in normalized and normalized["lot_sqft"] == "":
                    normalized["lot_sqft"] = None
                return normalized

    return None
