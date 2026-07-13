# scripts/test_regis.py

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PARCEL_QUERY_URL = (
    "https://311.memphistn.gov/server/rest/services/"
    "311/ParcelCentroids/MapServer/1/query"
)

DEFAULT_PARCEL_ID = "02701100015"


def fetch_parcel(parcel_id: str) -> dict:
    """Retrieve one Memphis parcel centroid in longitude/latitude."""

    parameters = {
      "where": (
    f"PARCELID = '{parcel_id}' "
    f"OR PARCELID2 = '{parcel_id}' "
    f"OR PARCELID = '{parcel_id.lstrip('0')}' "
    f"OR PARCELID2 = '{parcel_id.lstrip('0')}'"
),
        "outFields": "PARCELID,PARCELID2,MAP,PARCEL,CALC_ACRE,ZipCode,X,Y,POINT_X,POINT_Y",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }

    request_url = f"{PARCEL_QUERY_URL}?{urlencode(parameters)}"

    request = Request(
        request_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        raise RuntimeError(
            f"Memphis 311 returned HTTP {error.code}: {error.reason}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to Memphis 311: {error.reason}"
        ) from error


def main() -> None:
    parcel_id = (
        sys.argv[1].strip()
        if len(sys.argv) > 1
        else DEFAULT_PARCEL_ID
    )

    print(f"Querying Memphis 311 for parcel {parcel_id}...")

    result = fetch_parcel(parcel_id)

    if "error" in result:
        print("ArcGIS service returned an error:")
        print(json.dumps(result["error"], indent=2))
        sys.exit(1)

    features = result.get("features", [])

    if not features:
        print(f"No parcel found for parcel ID {parcel_id}.")
        sys.exit(1)

    feature = features[0]
    attributes = feature.get("attributes", {})
    geometry = feature.get("geometry") or {}

    longitude = geometry.get("x")
    latitude = geometry.get("y")

    print("\nParcel found.")
    print(f"PARCELID: {attributes.get('PARCELID', parcel_id)}")
    print(f"Longitude: {longitude}")
    print(f"Latitude: {latitude}")
    print(f"Geometry returned: {'Yes' if geometry else 'No'}")

    print("\nParcel attributes:")
    print(json.dumps(attributes, indent=2, default=str))


if __name__ == "__main__":
    main()