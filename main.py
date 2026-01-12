# main.py
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.rules import analyze
from app.data import load_parcel_from_csv

app = FastAPI(title="iNSITE MVP API", version="0.1.0")


# ---------- A) API Contract (Models) ----------

class AnalyzeRequest(BaseModel):
    city: Optional[str] = Field(
        default=None,
        description="City key like 'memphis' or 'nashville'. Required if parcel_id is used.",
    )
    parcel_id: Optional[str] = Field(
        default=None,
        description="Parcel ID to load from the city's CSV dataset.",
    )
    parcel: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw parcel dictionary. If provided, analysis runs on this directly.",
    )


# ---------- B) Health / Meta ----------

@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "iNSITE MVP API",
        "version": "0.1.0",
        "utc": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


# ---------- C) Core Endpoint ----------

@app.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    # 1) Determine parcel input
    if req.parcel is not None:
        parcel = req.parcel
    else:
        if not req.city or not req.parcel_id:
            raise HTTPException(
                status_code=400,
                detail="Provide either (parcel) OR (city + parcel_id).",
            )
        parcel = load_parcel_from_csv(city=req.city, parcel_id=req.parcel_id)
        if parcel is None:
            raise HTTPException(
                status_code=404,
                detail=f"Parcel not found for city='{req.city}' parcel_id='{req.parcel_id}'.",
            )

    # 2) Analyze
    result = analyze(parcel)

    # 3) Return
    return JSONResponse(content=result)

