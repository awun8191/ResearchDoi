import os

import requests
import urllib.parse

# This file is a manual smoke test. It has no default key.
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    raise SystemExit(
        "API_KEY is not set. Set API_KEY in the environment before you run this "
        "smoke test. The test sends the key in the X-Api-Key header and has no "
        "default value."
    )

try:
    doi = "10.1038/nphys1170"
    encoded_doi = urllib.parse.quote(doi, safe='')

    r = requests.get(
        f"http://localhost:8082/api/pdf/resolve?doi={encoded_doi}",
        headers={"X-Api-Key": API_KEY},
    )
    print("PDF Status:", r.status_code)
    print("PDF Response:", r.text)

except Exception as e:
    print("Request failed:", e)
