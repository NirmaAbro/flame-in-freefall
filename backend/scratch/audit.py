import os
import sys
import time
import json
import urllib.parse
from fastapi.testclient import TestClient

# Ensure backend is on sys.path
sys.path.insert(0, os.path.abspath("."))

from app.main import app
from app import schemas
import app.data_access as data_access

client = TestClient(app)
API = "/api/v1"

# Map routes to schema validator functions
def validate_schema(path, data):
    try:
        if path == "/health":
            schemas.Health.model_validate(data)
        elif path.startswith("/investigations") and "/variables" in path:
            schemas.VariablesResponse.model_validate(data)
        elif path == "/investigations" or path.startswith("/investigations?"):
            schemas.Paginated[schemas.InvestigationListItem].model_validate(data)
        elif path.startswith("/investigations/"):
            schemas.Investigation.model_validate(data)
        elif path == "/tests" or path.startswith("/tests?"):
            schemas.Paginated[schemas.TestRow].model_validate(data)
        elif path.startswith("/tests/"):
            schemas.TestRow.model_validate(data)
        elif path == "/habitats":
            if not isinstance(data, list):
                return False, "Not a list"
            for h in data:
                schemas.Habitat.model_validate(h)
        elif path.startswith("/rank"):
            schemas.RankResponse.model_validate(data)
        elif path == "/compare":
            schemas.CompareResponse.model_validate(data)
        elif path == "/analytics/coverage":
            schemas.CoverageResponse.model_validate(data)
        elif path == "/dashboard/summary":
            schemas.DashboardSummary.model_validate(data)
        elif path == "/filters":
            schemas.FilterOptions.model_validate(data)
        elif path == "/ai/search":
            schemas.AiSearchIntent.model_validate(data)
        elif path == "/ai/ask":
            schemas.AiAnswer.model_validate(data)
        return True, "valid"
    except Exception as e:
        return False, str(e)[:100]

def run_request(method, path, body=None, params=None):
    start = time.perf_counter()
    if method == "GET":
        r = client.get(f"{API}{path}", params=params)
    elif method == "POST":
        r = client.post(f"{API}{path}", json=body)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    source = r.headers.get("x-data-source", "none")
    
    validates = "n/a"
    if r.status_code == 200:
        if "text/csv" in r.headers.get("content-type", ""):
            validates = "csv-ok" if "id" in r.text else "csv-invalid"
        else:
            try:
                js = r.json()
                ok, msg = validate_schema(path, js)
                validates = "valid" if ok else f"invalid ({msg})"
            except Exception as e:
                validates = f"json-err ({e})"
    elif r.status_code == 422:
        validates = "422-val-err"
    elif r.status_code == 404:
        validates = "404-not-found"
    elif r.status_code == 503:
        validates = "503-svc-unavail"
    elif r.status_code == 500:
        validates = "500-server-err"
        
    return {
        "status": r.status_code,
        "validates": validates,
        "source": source,
        "elapsed_ms": round(elapsed_ms, 1),
        "body_preview": r.text[:100].replace("\n", " ")
    }

# Define all audit cases
test_cases = [
    # Health
    ("GET", "/health", None, None),
    # Dashboard
    ("GET", "/dashboard/summary", None, None),
    # Filters
    ("GET", "/filters", None, None),
    # Investigations list
    ("GET", "/investigations", None, None),
    ("GET", "/investigations", None, {"q": "bass"}),
    ("GET", "/investigations", None, {"hardware_family": "MSG"}),
    ("GET", "/investigations", None, {"page": 1, "page_size": 5}),
    ("GET", "/investigations", None, {"page_size": 101}), # 422
    # Investigations detail
    ("GET", "/investigations/PSI-25", None, None),
    ("GET", "/investigations/psi-25", None, None),
    ("GET", "/investigations/BASS-II", None, None),
    ("GET", "/investigations/psi-bass-ii", None, None),
    ("GET", "/investigations/unknown-inv-999", None, None), # 404
    # Investigations variables
    ("GET", "/investigations/PSI-25/variables", None, None),
    ("GET", "/investigations/psi-25/variables", None, None),
    ("GET", "/investigations/BASS-II/variables", None, None),
    ("GET", "/investigations/psi-bass-ii/variables", None, None),
    ("GET", "/investigations/unknown-inv-999/variables", None, None), # 404
    # Tests list & filters
    ("GET", "/tests", None, None),
    ("GET", "/tests", None, {"investigation_id": "PSI-25"}),
    ("GET", "/tests", None, {"investigation_id": "psi-25"}),
    ("GET", "/tests", None, {"investigation_id": "BASS-II"}),
    ("GET", "/tests", None, {"investigation_id": "psi-bass-ii"}),
    ("GET", "/tests", None, {"fuel": "PMMA"}),
    ("GET", "/tests", None, {"outcome": "extinction"}),
    ("GET", "/tests", None, {"min_oxygen": 20.0, "max_oxygen": 30.0}),
    ("GET", "/tests", None, {"min_pressure_kpa": 90.0, "max_pressure_kpa": 110.0}),
    ("GET", "/tests", None, {"page_size": 201}), # 422
    # Tests detail (URL-encoded)
    ("GET", "/tests/psi-bass-ii-b1", None, None),
    ("GET", "/tests/" + urllib.parse.quote("PSI-25:PSI-25_Experimental table_BASS-II.csv:1", safe=""), None, None),
    ("GET", "/tests/unknown-test-id", None, None), # 404
    # Habitats
    ("GET", "/habitats", None, None),
    # Export CSV
    ("GET", "/export/tests.csv", None, None),
    ("GET", "/export/tests.csv", None, {"investigation_id": "PSI-25"}),
    # Rank (4 real habitats + 2 fixture habitats + unknown)
    ("GET", "/rank", None, {"habitat": "iss"}),
    ("GET", "/rank", None, {"habitat": "gateway"}),
    ("GET", "/rank", None, {"habitat": "lunar-surface"}),
    ("GET", "/rank", None, {"habitat": "mars-transit"}),
    ("GET", "/rank", None, {"habitat": "moon-base"}),
    ("GET", "/rank", None, {"habitat": "spacesuit"}),
    ("GET", "/rank", None, {"habitat": "unknown-habitat-id"}), # 404
    ("GET", "/rank", None, None), # 422 missing param
    # Compare
    ("POST", "/compare", {"investigation_ids": ["PSI-25", "PSI-69"]}, None),
    ("POST", "/compare", {"investigation_ids": ["psi-bass-ii", "psi-flex"]}, None),
    ("POST", "/compare", "invalid-json-body", None), # 422
    # Analytics Coverage
    ("GET", "/analytics/coverage", None, None),
    # AI routes
    ("POST", "/ai/search", {"question": "materials that burn"}, None),
    ("POST", "/ai/ask", {"question": "What fuels were tested?", "investigation_ids": ["PSI-25"]}, None),
    # /explain
    ("GET", "/explain", None, None),
    ("POST", "/explain", {"question": "explain"}, None),
]

print("Starting audit with REAL CREDENTIALS (Supabase)...")
orig_has_cred = data_access.has_credentials
real_results = []
for method, path, body, params in test_cases:
    req_desc = f"{method} {path}"
    if params:
        req_desc += f"?{urllib.parse.urlencode(params)}"
    res = run_request(method, path, body, params)
    res["req"] = req_desc
    res["method"] = method
    res["path"] = path
    real_results.append(res)
    print(f"REAL: {req_desc:60} -> {res['status']} | {res['source']:18} | {res['validates']:10} | {res['elapsed_ms']}ms")

print("\nStarting audit with FIXTURE MODE (has_credentials = False)...")
data_access.has_credentials = lambda: False
fixture_results = []
for method, path, body, params in test_cases:
    req_desc = f"{method} {path}"
    if params:
        req_desc += f"?{urllib.parse.urlencode(params)}"
    res = run_request(method, path, body, params)
    res["req"] = req_desc
    res["method"] = method
    res["path"] = path
    fixture_results.append(res)
    print(f"FIXT: {req_desc:60} -> {res['status']} | {res['source']:18} | {res['validates']:10} | {res['elapsed_ms']}ms")

# Save full results as JSON
with open("scratch/audit_results.json", "w") as fp:
    json.dump({"real": real_results, "fixture": fixture_results}, fp, indent=2)

print("\nAudit completed and saved to scratch/audit_results.json")
