import os
import sys
import time
import json
import urllib.parse
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from app.main import app
from app import schemas
import app.data_access as data_access

client = TestClient(app)
API = "/api/v1"

def check_validation(path, data):
    try:
        if path == "/health":
            schemas.Health.model_validate(data)
        elif "/variables" in path:
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
        return False, str(e)[:60]

def execute_call(method, path, body=None, params=None):
    start = time.perf_counter()
    if method == "GET":
        r = client.get(f"{API}{path}", params=params)
    else:
        r = client.post(f"{API}{path}", json=body)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    
    src = r.headers.get("x-data-source", "none")
    status = r.status_code
    
    validates = "n/a"
    if status == 200:
        if "text/csv" in r.headers.get("content-type", ""):
            validates = "valid (csv)" if "id," in r.text or "id" in r.text[:20] else "invalid (csv)"
        else:
            try:
                js = r.json()
                ok, reason = check_validation(path, js)
                validates = "valid" if ok else f"invalid ({reason})"
            except Exception as e:
                validates = f"json error: {e}"
    elif status == 404:
        validates = "404 expected/returned"
    elif status == 422:
        validates = "422 expected/returned"
    elif status == 503:
        validates = "503 service unavailable"
        
    return {
        "status": status,
        "validates": validates,
        "source": src,
        "elapsed_ms": elapsed,
        "preview": r.text[:80].replace("\n", " ")
    }

# All routes to audit
routes = [
    # 1. health
    ("GET", "/health", None, None),
    # 2. dashboard/summary
    ("GET", "/dashboard/summary", None, None),
    # 3. filters
    ("GET", "/filters", None, None),
    # 4. investigations
    ("GET", "/investigations", None, None),
    ("GET", "/investigations", None, {"q": "bass"}),
    ("GET", "/investigations", None, {"hardware_family": "MSG"}),
    ("GET", "/investigations", None, {"page": 1, "page_size": 10}),
    ("GET", "/investigations", None, {"page_size": 101}), # 422
    # 5. investigations/{id}
    ("GET", "/investigations/PSI-25", None, None),
    ("GET", "/investigations/psi-25", None, None),
    ("GET", "/investigations/BASS-II", None, None),
    ("GET", "/investigations/psi-bass-ii", None, None),
    ("GET", "/investigations/unknown-id-404", None, None), # 404
    # 6. investigations/{id}/variables
    ("GET", "/investigations/PSI-25/variables", None, None),
    ("GET", "/investigations/psi-25/variables", None, None),
    ("GET", "/investigations/BASS-II/variables", None, None),
    ("GET", "/investigations/psi-bass-ii/variables", None, None),
    ("GET", "/investigations/unknown-id-404/variables", None, None), # 404
    # 7. tests
    ("GET", "/tests", None, None),
    ("GET", "/tests", None, {"investigation_id": "PSI-25"}),
    ("GET", "/tests", None, {"investigation_id": "psi-25"}),
    ("GET", "/tests", None, {"investigation_id": "BASS-II"}),
    ("GET", "/tests", None, {"investigation_id": "psi-bass-ii"}),
    ("GET", "/tests", None, {"fuel": "PMMA"}),
    ("GET", "/tests", None, {"outcome": "extinction"}),
    ("GET", "/tests", None, {"min_oxygen": 20.0, "max_oxygen": 25.0}),
    ("GET", "/tests", None, {"min_pressure_kpa": 90.0, "max_pressure_kpa": 110.0}),
    ("GET", "/tests", None, {"page_size": 201}), # 422
    # 8. tests/{id}
    ("GET", "/tests/" + urllib.parse.quote("PSI-25:PSI-25_Experimental table_BASS-II.csv:1", safe=""), None, None),
    ("GET", "/tests/psi-bass-ii-b1", None, None),
    ("GET", "/tests/unknown-test-404", None, None), # 404
    # 9. habitats
    ("GET", "/habitats", None, None),
    # 10. export/tests.csv
    ("GET", "/export/tests.csv", None, None),
    ("GET", "/export/tests.csv", None, {"investigation_id": "PSI-25"}),
    # 11. rank (4 real DB habitats + 2 fixture habitats + unknown)
    ("GET", "/rank", None, {"habitat": "iss"}),
    ("GET", "/rank", None, {"habitat": "gateway"}),
    ("GET", "/rank", None, {"habitat": "lunar-surface"}),
    ("GET", "/rank", None, {"habitat": "mars-transit"}),
    ("GET", "/rank", None, {"habitat": "moon-base"}),
    ("GET", "/rank", None, {"habitat": "spacesuit"}),
    ("GET", "/rank", None, {"habitat": "unknown-habitat"}), # 404
    ("GET", "/rank", None, None), # 422
    # 12. compare
    ("POST", "/compare", {"investigation_ids": ["PSI-25", "PSI-69"]}, None),
    ("POST", "/compare", {"investigation_ids": ["psi-bass-ii", "psi-flex"]}, None),
    ("POST", "/compare", "invalid-body-not-dict", None), # 422
    # 13. analytics/coverage
    ("GET", "/analytics/coverage", None, None),
    # 14. ai routes
    ("POST", "/ai/search", {"question": "materials that burn"}, None),
    ("POST", "/ai/ask", {"question": "What was tested in PSI-25?", "investigation_ids": ["PSI-25"]}, None),
    # 15. explain (present in README text as 'Explain this selection is POST /ai/ask')
    ("GET", "/explain", None, None),
]

print("Running REAL audit...", flush=True)
real_map = {}
for m, p, b, q in routes:
    label = f"{m} {p}" + (f"?{urllib.parse.urlencode(q)}" if q else "")
    res = execute_call(m, p, b, q)
    real_map[label] = res
    print(f"REAL: {label:55} | status={res['status']} | src={res['source']} | time={res['elapsed_ms']}ms", flush=True)

print("\nRunning FIXTURE audit...", flush=True)
data_access.has_credentials = lambda: False
fixture_map = {}
for m, p, b, q in routes:
    label = f"{m} {p}" + (f"?{urllib.parse.urlencode(q)}" if q else "")
    res = execute_call(m, p, b, q)
    fixture_map[label] = res
    print(f"FIXT: {label:55} | status={res['status']} | src={res['source']} | time={res['elapsed_ms']}ms", flush=True)

# Save combined audit
audit_data = []
for m, p, b, q in routes:
    label = f"{m} {p}" + (f"?{urllib.parse.urlencode(q)}" if q else "")
    r = real_map[label]
    f = fixture_map[label]
    
    # Identify problem
    problems = []
    if r["source"] == "none" and r["status"] == 200:
        problems.append("Missing X-Data-Source in real mode")
    if f["source"] == "none" and f["status"] == 200:
        problems.append("Missing X-Data-Source in fixture mode")
    if r["status"] == 404 and ("psi-bass-ii" in label or "BASS-II" in label or "psi-25" in label or "PSI-25" in label):
        problems.append("404 on BASS-II/PSI-25 alias")
    if f["status"] == 404 and ("psi-bass-ii" in label or "BASS-II" in label or "psi-25" in label or "PSI-25" in label):
        problems.append("404 in fixture mode on alias")
    if r["status"] >= 500:
        problems.append(f"Server error {r['status']}")
    if f["status"] >= 500:
        problems.append(f"Fixture server error {f['status']}")
    if "invalid" in r["validates"]:
        problems.append(f"Real body schema invalid: {r['validates']}")
    if "invalid" in f["validates"]:
        problems.append(f"Fixture body schema invalid: {f['validates']}")
    if r["status"] == 404 and p == "/explain":
        problems.append("Not registered (README says it's POST /ai/ask)")
        
    problem_str = "; ".join(problems) if problems else "None"
    
    audit_data.append({
        "route": label,
        "real_status": r["status"],
        "fixture_status": f["status"],
        "real_source": r["source"],
        "fixture_source": f["source"],
        "real_validates": r["validates"],
        "fixture_validates": f["validates"],
        "problem": problem_str
    })

with open("scratch/full_audit.json", "w") as fp:
    json.dump(audit_data, fp, indent=2)

print("\nSaved full audit to scratch/full_audit.json", flush=True)
