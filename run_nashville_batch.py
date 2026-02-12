import json
from pathlib import Path

import pandas as pd
from app.rules import analyze

INPUT = Path("data/nashville/parcels.csv")
OUTPUT = Path("data/nashville/results.jsonl")

def main():
    df = pd.read_csv(INPUT)

    # Minimal required columns check
    if "parcel_id" not in df.columns or "lot_size" not in df.columns:
        raise ValueError("Missing required columns: parcel_id and/or lot_size")

    with OUTPUT.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            parcel = {
    "city": "nashville",
    "parcel_id": row["parcel_id"],
    "zoning": row["Zoning"] if pd.notna(row["Zoning"]) else None,

    # provide lot size in square feet under the key the engine expects
    "lot_sqft": float(row["lot_size"]) if pd.notna(row["lot_size"]) else None,

    # keep this too (harmless) in case other parts use it
    "lot_size": float(row["lot_size"]) if pd.notna(row["lot_size"]) else None,
}

            result = analyze(parcel)
            f.write(json.dumps(result))
            f.write("\n")

    print(f"Nashville batch complete. Wrote: {OUTPUT}")

if __name__ == "__main__":
    main()