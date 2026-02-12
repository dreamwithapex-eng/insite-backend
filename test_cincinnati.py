import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API = "https://insite-backend.onrender.com/v1/submit"

payload = {"city": "cincinnati", "parcel_id": "050002130148"}

req = Request(
    API,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)

try:
    resp = urlopen(req)
    print("OK", resp.status)
    print(resp.read()[:300])
except HTTPError as e:
    print("HTTP", e.code)
    print(e.read()[:300])
