# app/main.py
from typing import Any, Dict, Optional, List
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from app.rules import analyze
from app.data import load_parcel_from_csv

app = FastAPI(title="iNSITE MVP API", version="0.1.0")

# ---------- A) API Contract (Models) ----------

class AnalyzeRequest(BaseModel):
    city: Optional[str] = Field(default=None, description="City key like 'memphis' or 'nashville'")
    parcel_id: Optional[str] = Field(default=None, description="Parcel ID to look up from city CSV")
    parcel: Optional[Dict[str, Any]] = Field(default=None, description="Parcel record as JSON object")

from typing import List  # add this near the top if not already present

class AnalyzeResponse(BaseModel):
    score: int
    tier: str
    flags: List[str]
    explanations: List[str]
    ruleset_version: str
    analyzed_at: str


# ---------- D) Health Check ----------

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

# ---------- B/C) Wiring + Validation + Errors ----------

@app.post("/analyze", response_model=AnalyzeResponse, responses={400: {"model": dict}, 404: {"model": dict}})
def analyze_endpoint(req: AnalyzeRequest):
    # Simple request logging
    print(f"[REQUEST] /analyze city={req.city} parcel_id={req.parcel_id} has_parcel={'yes' if req.parcel else 'no'}")

    # Validation rule:
    # - You must provide either:
    #   (1) req.parcel (a full record), OR
    #   (2) req.city + req.parcel_id (so we can look up from CSV)
    if req.parcel is None:
        if not req.city or not req.parcel_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_REQUEST",
                    "message": "Provide either 'parcel' OR both 'city' and 'parcel_id'.",
                    "required": ["parcel OR (city + parcel_id)"],
                },
            )

        parcel = load_parcel_from_csv(req.city, req.parcel_id)
        if parcel is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PARCEL_NOT_FOUND",
                    "message": f"Parcel '{req.parcel_id}' not found for city '{req.city}'.",
                    "hint": "Ensure data/<city>.csv exists and contains a 'parcel_id' column.",
                },
            )
    else:
        parcel = req.parcel

    # Call the brain
    result = analyze(parcel)

    # Basic output coercion for response model
    return {
        "score": int(result["score"]),
        "tier": result["tier"],
        "flags": result["flags"],
        "explanations": result["explanations"],
        "ruleset_version": result["ruleset_version"],
        "analyzed_at": result["analyzed_at"],
    }
