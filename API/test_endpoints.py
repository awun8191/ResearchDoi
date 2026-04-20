import requests
import urllib.parse
try:
    doi = "10.1038/nphys1170"
    encoded_doi = urllib.parse.quote(doi, safe='')
    
    r = requests.get(f"http://localhost:8082/api/pdf/resolve?doi={encoded_doi}", headers={"X-Api-Key": "nas"})
    print("PDF Status:", r.status_code)
    print("PDF Response:", r.text)

except Exception as e:
    print("Request failed:", e)
