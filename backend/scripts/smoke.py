"""HTTP smoke checks for the IGNIS API."""
from __future__ import annotations

import argparse
import sys
import time
from urllib.parse import quote

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    failures = 0

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        def call(
            method: str,
            path: str,
            *,
            expected: set[int] = {200},
            json: object = None,
            content: str | None = None,
            params: dict[str, object] | None = None,
        ) -> httpx.Response:
            nonlocal failures
            started = time.perf_counter()
            elapsed = (time.perf_counter() - started) * 1000
            try:
                response = client.request(
                    method,
                    path,
                    json=json,
                    content=content,
                    params=params,
                )
            except httpx.HTTPError as error:
                failures += 1
                print(f"{method} {path} 0 error {elapsed:.1f}ms")
                return httpx.Response(
                    status_code=0,
                    request=httpx.Request(method, path),
                    extensions={"smoke_error": str(error)},
                )
            elapsed = (time.perf_counter() - started) * 1000
            source = response.headers.get("x-data-source", "none")
            print(f"{method} {path} {response.status_code} {source} {elapsed:.1f}ms")
            if response.status_code not in expected:
                failures += 1
            return response

        call("GET", "/api/v1/health")
        call("GET", "/api/v1/dashboard/summary")
        call("GET", "/api/v1/filters")
        call("GET", "/api/v1/investigations")
        call("GET", "/api/v1/investigations", params={"q": "bass"})
        call(
            "GET",
            "/api/v1/investigations",
            params={"hardware_family": "fan"},
        )
        call(
            "GET",
            "/api/v1/investigations",
            params={"page": 1, "page_size": 25},
        )
        call(
            "GET",
            "/api/v1/investigations",
            params={"page_size": 101},
            expected={422},
        )

        for investigation_id in ("PSI-25", "psi-25", "BASS-II", "unknown-id"):
            call(
                "GET",
                f"/api/v1/investigations/{quote(investigation_id, safe='')}",
                expected={200, 404} if investigation_id == "unknown-id" else {200},
            )
        for investigation_id in ("PSI-25", "psi-25", "BASS-II", "unknown-id"):
            call(
                "GET",
                f"/api/v1/investigations/{quote(investigation_id, safe='')}/variables",
                expected={200, 404} if investigation_id == "unknown-id" else {200},
            )

        call("GET", "/api/v1/tests")
        call(
            "GET",
            "/api/v1/tests",
            params={"investigation_id": "PSI-25"},
        )
        call(
            "GET",
            "/api/v1/tests",
            params={"investigation_id": "psi-25"},
        )
        call("GET", "/api/v1/tests", params={"fuel": "PMMA"})
        call("GET", "/api/v1/tests", params={"outcome": "extinction"})
        call(
            "GET",
            "/api/v1/tests",
            params={"min_oxygen": 20, "max_oxygen": 25},
        )
        call(
            "GET",
            "/api/v1/tests",
            params={"min_pressure_kpa": 90, "max_pressure_kpa": 110},
        )
        call(
            "GET",
            "/api/v1/tests",
            params={"page_size": 201},
            expected={422},
        )
        tests_response = call(
            "GET",
            "/api/v1/tests",
            expected={200},
            params={"investigation_id": "PSI-25"},
        )
        test_items = tests_response.json().get("items", [])
        if test_items:
            test_id = quote(test_items[0]["id"], safe="")
            call("GET", f"/api/v1/tests/{test_id}")
        else:
            failures += 1
            print("GET /api/v1/tests/{first-id} 0 none 0.0ms")
        call("GET", "/api/v1/tests/unknown-test", expected={404})

        habitats_response = call("GET", "/api/v1/habitats")
        habitats = habitats_response.json() if habitats_response.status_code == 200 else []
        for habitat in habitats[:4]:
            habitat_id = quote(habitat["id"], safe="")
            call("GET", "/api/v1/rank", params={"habitat": habitat_id})
        call(
            "GET",
            "/api/v1/rank",
            params={"habitat": "unknown-habitat"},
            expected={404},
        )
        call("GET", "/api/v1/rank", expected={422})

        call(
            "GET",
            "/api/v1/export/tests.csv",
            params={"investigation_id": "PSI-25"},
        )
        call(
            "POST",
            "/api/v1/compare",
            json={"investigation_ids": ["PSI-25", "PSI-69"]},
        )
        call(
            "POST",
            "/api/v1/compare",
            content="{invalid json",
            expected={422},
        )
        call("GET", "/api/v1/analytics/coverage")
        call(
            "POST",
            "/api/v1/ai/search",
            json={"question": ""},
        )
        call(
            "POST",
            "/api/v1/ai/ask",
            json={"question": ""},
        )
        call("GET", "/api/v1/explain", expected={404})

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
