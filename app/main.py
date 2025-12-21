# app/main.py
from typing import Any, Dict, Optional, List
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.rules import analyze
from app.data import load_parcel_from_csv

app = FastAPI(title="iNSITE MVP API", version="0.1.0")

# ---------- CORS (Carrd + local testing) ----------
# Carrd serves pages from multiple subdomains (published + preview/editor),
# so we explicitly allow your site and safely regex-allow carrd.co.
EXACT_ORIGINS = [
    "https://insitehq.carrd.co",
    "https://www.insitehq.carrd.co",
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=EXACT_ORIGINS,
    allow_origin_regex=r"^https://([a-z0-9-]+\.)*carrd\.co$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- API Contract (Models) ----------

class AnalyzeRequest(BaseModel):
    city: Optional[str] = Field(default=None)
    parcel_id: Optional[str] = Field(default=None)
    parcel: Optional[Dict[str, Any]] = Field(default=None)


class AnalyzeResponse(BaseModel):
    score: int
    tier: str
    flags: List[str]
    explanations: List[str]
    ruleset_version: str
    analyzed_at: str


# ---------- Health Check ----------

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


# ---------- Analysis Endpoint ----------

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    if req.parcel is None:
        if not req.city or not req.parcel_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_REQUEST",
                    "message": "Provide either 'parcel' OR both 'city' and 'parcel_id'.",
                },
            )

        parcel = load_parcel_from_csv(req.city, req.parcel_id)
        if parcel is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PARCEL_NOT_FOUND",
                    "message": f"Parcel '{req.parcel_id}' not found for city '{req.city}'.",
                },
            )
    else:
        parcel = req.parcel

    result = analyze(parcel)

    return {
        "score": int(result["score"]),
        "tier": result["tier"],
        "flags": result["flags"],
        "explanations": result["explanations"],
        "ruleset_version": result["ruleset_version"],
        "analyzed_at": result["analyzed_at"],
    }


# ---------- Stable Public Contract ----------

@app.post("/v1/submit", response_model=AnalyzeResponse)
def submit(req: AnalyzeRequest):
    return analyze_endpoint(req)

