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

def probe_one(label, method, path, body=None, params=None):
    start = time.perf_counter()
    try:
        if method == "GET":
            r = client.get(f"{API}{path}", params=params, timeout=10.0)
        else:
            r = client.post(f"{API}{path}", json=body, timeout=10.0)
        dur = round((time.perf_counter() - start) * 1000, 1)
        src = r.headers.get("x-data-source", "none")
        print(f"[{dur:6.1f}ms] {label} -> {r.status_code} (src={src}): {r.text[:80]}", flush=True)
        return r.status_code, src, dur, r.text[:120]
    except Exception as e:
        dur = round((time.perf_counter() - start) * 1000, 1)
        print(f"[{dur:6.1f}ms] {label} -> EXCEPTION: {e}", flush=True)
        return 0, "err", dur, str(e)

routes_to_test = [
    ("Health", "GET", "/health", None, None),
    ("Dashboard Summary", "GET", "/dashboard/summary", None, None),
    ("Filters", "GET", "/filters", None, None),
    ("Investigations list", "GET", "/investigations", None, None),
    ("Investigations q=bass", "GET", "/investigations", None, {"q": "bass"}),
    ("Investigations hardware=MSG", "GET", "/investigations", None, {"hardware_family": "MSG"}),
    ("Investigations paged", "GET", "/investigations", None, {"page": 1, "page_size": 5}),
    ("Investigations bad page_size", "GET", "/investigations", None, {"page_size": 101}),
    ("Investigation PSI-25", "GET", "/investigations/PSI-25", None, None),
    ("Investigation psi-25", "GET", "/investigations/psi-25", None, None),
    ("Investigation BASS-II", "GET", "/investigations/BASS-II", None, None),
    ("Investigation psi-bass-ii", "GET", "/investigations/psi-bass-ii", None, None),
    ("Investigation unknown", "GET", "/investigations/unknown-999", None, None),
    ("Variables PSI-25", "GET", "/investigations/PSI-25/variables", None, None),
    ("Variables psi-25", "GET", "/investigations/psi-25/variables", None, None),
    ("Variables BASS-II", "GET", "/investigations/BASS-II/variables", None, None),
    ("Variables psi-bass-ii", "GET", "/investigations/psi-bass-ii/variables", None, None),
    ("Variables unknown", "GET", "/investigations/unknown-999/variables", None, None),
    ("Tests list", "GET", "/tests", None, None),
    ("Tests inv=PSI-25", "GET", "/tests", None, {"investigation_id": "PSI-25"}),
    ("Tests inv=psi-25", "GET", "/tests", None, {"investigation_id": "psi-25"}),
    ("Tests inv=BASS-II", "GET", "/tests", None, {"investigation_id": "BASS-II"}),
    ("Tests inv=psi-bass-ii", "GET", "/tests", None, {"investigation_id": "psi-bass-ii"}),
    ("Tests fuel=PMMA", "GET", "/tests", None, {"fuel": "PMMA"}),
    ("Tests outcome=extinction", "GET", "/tests", None, {"outcome": "extinction"}),
    ("Tests oxygen 20-30", "GET", "/tests", None, {"min_oxygen": 20.0, "max_oxygen": 30.0}),
    ("Tests pressure 90-110", "GET", "/tests", None, {"min_pressure_kpa": 90.0, "max_pressure_kpa": 110.0}),
    ("Tests bad page_size", "GET", "/tests", None, {"page_size": 201}),
    ("Test row encoded", "GET", "/tests/" + urllib.parse.quote("PSI-25:PSI-25_Experimental table_BASS-II.csv:1", safe=""), None, None),
    ("Test row unknown", "GET", "/tests/unknown-test-id", None, None),
    ("Habitats", "GET", "/habitats", None, None),
    ("Export CSV", "GET", "/export/tests.csv", None, None),
    ("Export CSV inv=PSI-25", "GET", "/export/tests.csv", None, {"investigation_id": "PSI-25"}),
    ("Rank iss", "GET", "/rank", None, {"habitat": "iss"}),
    ("Rank gateway", "GET", "/rank", None, {"habitat": "gateway"}),
    ("Rank lunar-surface", "GET", "/rank", None, {"habitat": "lunar-surface"}),
    ("Rank mars-transit", "GET", "/rank", None, {"habitat": "mars-transit"}),
    ("Rank moon-base", "GET", "/rank", None, {"habitat": "moon-base"}),
    ("Rank spacesuit", "GET", "/rank", None, {"habitat": "spacesuit"}),
    ("Rank unknown", "GET", "/rank", None, {"habitat": "unknown-hab"}),
    ("Rank missing param", "GET", "/rank", None, None),
    ("Compare 2 invs", "POST", "/compare", {"investigation_ids": ["PSI-25", "PSI-69"]}, None),
    ("Compare invalid body", "POST", "/compare", "bad-body", None),
    ("Analytics coverage", "GET", "/analytics/coverage", None, None),
    ("AI search", "POST", "/ai/search", {"question": "flame speed"}, None),
    ("AI ask", "POST", "/ai/ask", {"question": "summary", "investigation_ids": ["PSI-25"]}, None),
    ("Explain route", "GET", "/explain", None, None),
]

print("=== AUDIT WITH REAL CREDENTIALS ===", flush=True)
for label, m, p, b, q in routes_to_test:
    probe_one(label, m, p, b, q)

print("\n=== AUDIT WITH FIXTURES (has_credentials = False) ===", flush=True)
data_access.has_credentials = lambda: False
for label, m, p, b, q in routes_to_test:
    probe_one(label, m, p, b, q)
