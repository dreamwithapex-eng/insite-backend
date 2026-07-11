# scripts/test_regis.py

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REGIS_QUERY_URL = (
    "https://gis.shelbycountytn.gov/arcgis/rest/services/"
    "Parcel/CERT_Parcel/MapServer/0/query"
)

DEFAULT_PARCEL_ID = "02701100015"


def fetch_parcel(parcel_id: str) -> dict:
    """Retrieve one Shelby County parcel and its polygon geometry."""

    parameters = {
        "where": f"PARCELID = '{parcel_id}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }

    request_url = f"{REGIS_QUERY_URL}?{urlencode(parameters)}"
    request = Request(
        request_url,
        headers={
            "User-Agent": "iNSITE-Parcel-Enrichment/0.1",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        raise RuntimeError(
            f"ReGIS returned HTTP {error.code}: {error.reason}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to ReGIS: {error.reason}"
        ) from error


def main() -> None:
    parcel_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PARCEL_ID
    parcel_id = parcel_id.strip()

    print(f"Querying Shelby County ReGIS for parcel {parcel_id}...")

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
    geometry = feature.get("geometry")

    print("\nParcel found.")
    print(f"PARCELID: {attributes.get('PARCELID', parcel_id)}")

    possible_address_fields = [
        "PAR_ADDR1",
        "ADDRESS",
        "SITEADDR",
        "SITE_ADDRESS",
    ]

    address = next(
        (
            attributes.get(field)
            for field in possible_address_fields
            if attributes.get(field)
        ),
        "Address field not identified",
    )

    print(f"Address: {address}")
    print(f"Geometry returned: {'Yes' if geometry else 'No'}")

    if geometry:
        rings = geometry.get("rings", [])
        print(f"Polygon rings: {len(rings)}")

    print("\nFull parcel attributes:")
    print(json.dumps(attributes, indent=2, default=str))


if __name__ == "__main__":
    main()