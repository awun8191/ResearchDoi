import sys
from src.service.arxiv_lookup import ArxivLookup
from src.service.doi_lookup import DoiLookup

identifier = "10.1038/nphys1170"
if len(sys.argv) > 1: 
    identifier = sys.argv[1]

arxiv_svc = ArxivLookup()
doi_svc = DoiLookup()

print(f"--- LOOKING UP: {identifier} ---")

# 1. Try ArXiv
res = arxiv_svc.fetch_metadata(identifier)
if res:
    print("SOURCE: ArXiv")
    print("RESULT:", res)
else:
    print("ArXiv: No results found.")
    # 2. Try CrossRef
    try:
        res = doi_svc.fetch_metadata(identifier)
        if res:
            print("SOURCE: CrossRef")
            print("RESULT:", res)
        else:
            print("CrossRef: No results found.")
    except Exception as e:
        print("CrossRef ERROR:", e)
