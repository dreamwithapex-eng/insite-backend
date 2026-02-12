import csv
import time
import json
from collections import Counter
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API = "https://insite-backend.onrender.com/v1/submit"
CITY = "cincinnati"

# Read parcel_ids from the production lookup CSV
parcel_ids = []
with open("data/cincinnati/parcels.csv", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        pid = str(r.get("parcel_id", "")).strip()
        if pid:
            parcel_ids.append(pid)

print(f"Running {len(parcel_ids)} parcels through production…")

results = []
tiers = Counter()

for i, parcel_id in enumerate(parcel_ids, 1):
    payload = json.dumps({
        "city": CITY,
        "parcel_id": parcel_id
    }).encode("utf-8")

    req = Request(
        API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            status = resp.status

    except HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8")
        data = {"error": body}

    except URLError as e:
        status = "NETWORK_ERROR"
        data = {"error": str(e)}

    if status != 200:
        print(f"{i}/{len(parcel_ids)} → {parcel_id} → ERROR {status}")
        results.append({
            "parcel_id": parcel_id,
            "status": status,
            "score": "",
            "tier": "",
            "ruleset_version": "",
            "analyzed_at": "",
            "error": str(data),
        })
    else:
        tier = data.get("tier")
        tiers[tier] += 1
        print(f"{i}/{len(parcel_ids)} → {parcel_id} → {tier} {data.get('score')}")
        results.append({
            "parcel_id": parcel_id,
            "status": status,
            "score": data.get("score"),
            "tier": tier,
            "ruleset_version": data.get("ruleset_version"),
            "analyzed_at": data.get("analyzed_at"),
            "error": "",
        })

    time.sleep(0.15)  # polite throttle

with open("calibration_results_v0.1_production.csv", "w", newline="") as f:
    fieldnames = [
        "parcel_id",
        "status",
        "score",
        "tier",
        "ruleset_version",
        "analyzed_at",
        "error",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print("\nSaved: calibration_results_v0.1_production.csv")
print("Tier counts:", dict(tiers))

