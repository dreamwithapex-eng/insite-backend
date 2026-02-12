# scripts/normalize_cincinnati.py

from pathlib import Path
import csv
import sys

import pandas as pd


def strip_nul_bytes(src_path: Path, dst_path: Path) -> None:
    """
    Cincinnati exports sometimes contain NUL bytes, which can break CSV parsers.
    This writes a sanitized copy with NUL bytes removed.
    """
    with src_path.open("rb") as f_in, dst_path.open("wb") as f_out:
        for chunk in iter(lambda: f_in.read(1024 * 1024), b""):
            f_out.write(chunk.replace(b"\x00", b""))


def read_csv_safely(path: Path) -> pd.DataFrame:
    """
    Read with robust defaults for municipal exports.
    - latin1 covers many non-utf8 bytes without crashing
    - engine='c' is fastest; if it fails, we fallback
    - on_bad_lines='skip' prevents a single corrupt row from killing the run
    """
    # Try fast path first
    try:
        return pd.read_csv(
            path,
            sep=",",
            encoding="latin1",
            engine="c",
            dtype=str,
            on_bad_lines="skip"
        )
    except TypeError:
        # Older pandas (pre on_bad_lines) fallback
        return pd.read_csv(
            path,
            sep=",",
            encoding="latin1",
            engine="c",
            dtype=str,
            error_bad_lines=False,
            warn_bad_lines=True
        )
    except Exception:
        # Final fallback: python engine + csv module sniffing
        return pd.read_csv(
            path,
            sep=",",
            encoding="latin1",
            engine="python",
            dtype=str
        )


def main() -> int:
    # Adjust these ONLY if your filenames differ
    RAW_PATH = Path("data/cincinnati/cincinnati_parcels_raw.csv")
    CLEAN_TMP = Path("data/cincinnati/_tmp_no_nul.csv")
    OUT_PATH = Path("data/processed/cincinnati_parcels.csv")

    if not RAW_PATH.exists():
        print("ERROR: Raw file not found at:", RAW_PATH)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1) Remove NUL bytes (if any)
    print("Sanitizing (removing NUL bytes) ->", CLEAN_TMP)
    strip_nul_bytes(RAW_PATH, CLEAN_TMP)

    # 2) Read CSV robustly
    print("Reading CSV ->", CLEAN_TMP)
    df = read_csv_safely(CLEAN_TMP)

    # 3) Validate required columns
    required = ["PARCELID", "ACREDEED", "CLASS"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print("ERROR: Missing expected columns:", missing)
        print("Found columns:", list(df.columns)[:50])
        return 1

    # 4) Normalize
    # parcel_id
    parcel_id = df["PARCELID"].fillna("").astype(str)

    # zoning (Cincinnati CLASS is numeric-ish; treat as string)
    zoning = df["CLASS"].fillna("").astype(str)

    # lot_sqft = ACREDEED * 43560
    # Convert safely (non-numeric -> NaN -> 0)
    acres = pd.to_numeric(df["ACREDEED"], errors="coerce").fillna(0)
    lot_sqft = acres * 43560

    df_out = pd.DataFrame({
        "parcel_id": parcel_id,
        "city": "Cincinnati",
        "lot_sqft": lot_sqft,
        "zoning": zoning
    })

    # Keep only valid land area
    df_out = df_out[df_out["lot_sqft"] > 0]

    # 5) Write output
    df_out.to_csv(OUT_PATH, index=False)
    print("Cincinnati normalized:", len(df_out), "parcels written to", str(OUT_PATH))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())