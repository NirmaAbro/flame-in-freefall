"""T5 checks: compare, coverage and variables (backend/app/analytics and three route files).

The test names carry the ids of the T5 plan: G1, G2, A1 to A14, B1 to B12, C1 to C8,
D1 to D11, E1 to E4. F1 and F2 of the plan are checks on the whole suite, not tests here.

Every test runs with no network, no database and no model.

Run from the backend folder:  python -m pytest
"""
import ast
import copy
import importlib
import itertools
import json
import socket
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import data_access, fixtures, schemas
from app.main import app

API = "/api/v1"
client = TestClient(app)
BACKEND = Path(__file__).resolve().parents[1]

# ---------- The fixed texts of the three answers ----------

STORED = "Values are shown exactly as stored. Missing values are 'not reported', never zero."
CHARTS = "Numeric charts appear only when two or more records report the same parameter in the same unit."
ROW_CHARTS = "A chart of test rows shows the lowest and the highest value in the indexed test rows of each record."
ONE_MISSING = "1 selected record was not found."
TWO_MISSING = "2 selected records were not found."
FIRST_FOUR = "Only the first 4 selected records were used."
TOO_FEW = "A comparison needs at least 2 records."
SAMPLE = "This answer uses sample data, not verified PSI data."
PARSED = "This answer uses data that a program read from PSI tables. No person checked it."

COUNT = "Each number is the count of indexed records with that topic and that fuel class."
MULTI = "A record with several topics or fuel classes counts in each cell that matches."
GAP = "A gap means that no indexed record matches. It does not mean that no research exists."
ONE_UNPLACED = "1 indexed record matches no listed topic or no listed fuel class. The map does not show it."
THREE_UNPLACED = "3 indexed records match no listed topic or no listed fuel class. The map does not show them."

NO_ROWS = "No test rows are indexed for this record."

ROW_NAMES = [
    "Research area",
    "Platform",
    "Gravity environment",
    "Hardware",
    "Fuel class",
    "Fuels / materials",
    "Topics",
    "Measurement types",
    "Reported conditions",
    "Linked files",
]
FIELDS = ["fuel", "geometry", "oxygen_pct", "pressure_kpa", "flow_cm_s", "diluent", "outcome"]
EMPTY_COMPARISON = {"investigations": [], "rows": [], "comparable_parameters": []}
PSI_HOME = "https://psi.nasa.gov/physci/repo"


class _Modules:
    """app.analytics.<name>, imported on first use, so each test fails on its own before the code exists."""

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return importlib.import_module(f"app.analytics.{name}")


m = _Modules()


# ---------- Guard ----------


@pytest.fixture(autouse=True)
def guard(monkeypatch):
    """No key in the environment, and no connection to an address outside this computer."""
    for name in ("LLM_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        monkeypatch.delenv(name, raising=False)
    real_connect = socket.socket.connect

    def local_only(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host in ("127.0.0.1", "::1"):  # the test client needs a local connection on Windows
            return real_connect(self, address)
        raise OSError(f"a test tried to open a network connection to {address!r}")

    def blocked_post(*args, **kwargs):
        raise AssertionError("a test tried to reach the network")

    monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(httpx, "post", blocked_post)


# ---------- Helpers ----------


def compare(ids):
    """POST /compare. Every answer gets the checks that the Compare page depends on."""
    response = client.post(API + "/compare", json={"investigation_ids": ids})
    assert response.status_code == 200, response.text
    body = response.json()
    schemas.CompareResponse.model_validate(body)
    shown = [item["id"] for item in body["investigations"]]
    names = [row["field"] for row in body["rows"]]
    pairs = [(parameter["name"], parameter["unit"]) for parameter in body["comparable_parameters"]]
    # The page uses these values as list keys, so none may repeat.
    assert len(shown) == len(set(shown))
    assert len(names) == len(set(names))
    assert len(pairs) == len(set(pairs))
    assert len(body["notes"]) == len(set(body["notes"]))
    for row in body["rows"]:
        assert set(row["cells"]) == set(shown) and len(row["cells"]) == len(shown)  # one cell for each record
        for cell in row["cells"].values():  # a missing value is null, never an empty text
            assert cell["value"] is None or cell["value"].strip()
    for parameter in body["comparable_parameters"]:
        bars = [(value["investigation_id"], value["label"]) for value in parameter["values"]]
        owners = {record_id for record_id, _ in bars}
        assert len(bars) == len(set(bars))  # two values of one record never share a label
        assert owners <= set(shown) and len(owners) >= 2  # a chart needs two different records
    return body


def table(body):
    """The compare rows as {row name: [cell text for each record, in the order of the records]}."""
    shown = [item["id"] for item in body["investigations"]]
    return {row["field"]: [row["cells"][record_id]["value"] for record_id in shown] for row in body["rows"]}


def charts(body):
    """The comparable numbers as [(name, unit, [(record id, label, value), ...]), ...]."""
    return [
        (p["name"], p["unit"], [(v["investigation_id"], v["label"], v["value"]) for v in p["values"]])
        for p in body["comparable_parameters"]
    ]


def coverage():
    """GET /analytics/coverage. Every answer gets the checks that the Research Map page depends on."""
    response = client.get(API + "/analytics/coverage")
    assert response.status_code == 200, response.text
    body = response.json()
    schemas.CoverageResponse.model_validate(body)
    places = [(cell["row"], cell["column"]) for cell in body["cells"]]
    assert places == [(row, column) for row in body["rows"] for column in body["columns"]]  # complete, row by row
    for cell in body["cells"]:
        assert cell["count"] == len(cell["investigation_ids"]) == len(set(cell["investigation_ids"]))
    assert len(body["method_notes"]) == len(set(body["method_notes"]))
    return body


def counts(body):
    """The counts as one list for each row of the matrix."""
    width = len(body["columns"])
    numbers = [cell["count"] for cell in body["cells"]]
    return [numbers[start : start + width] for start in range(0, len(numbers), width)]


def cell_ids(body, row, column):
    return next(cell for cell in body["cells"] if (cell["row"], cell["column"]) == (row, column))["investigation_ids"]


def variables(record_id):
    """GET /investigations/{id}/variables for a known record."""
    response = client.get(f"{API}/investigations/{record_id}/variables")
    assert response.status_code == 200, response.text
    body = response.json()
    schemas.VariablesResponse.model_validate(body)
    assert body["investigation_id"] == record_id
    assert len(body["notes"]) == len(set(body["notes"]))
    for entry in body["variables"]:
        assert len(entry["values"]) == len(set(entry["values"])) <= 12
    return body


def entry(body, field):
    return next(item for item in body["variables"] if item["field"] == field)


def var(field, status, values=(), minimum=None, maximum=None):
    return {"field": field, "status": status, "values": list(values), "minimum": minimum, "maximum": maximum}


def on_disk(name):
    return json.loads((fixtures.FIXTURES / name).read_text(encoding="utf-8"))


def sample_data_is_unchanged():
    """The cached sample data equals the files. A copy taken in the test would hide a change made earlier."""
    return (
        fixtures.investigations() == on_disk("investigations.json")
        and fixtures.tests() == on_disk("tests.json")
        and fixtures.meta() == on_disk("meta.json")
    )


# ---------- Made-up data ----------

TOPICS = ["T1", "T2", "T3"]
FUELS = ["Solid", "Gas"]


def record(record_id, **fields):
    """A full record of the contract. The id starts with x-, so no sample record can stand in for it."""
    base = {
        "id": record_id,
        "source_id": record_id.upper(),
        "title": f"Title of {record_id}",
        "acronym": record_id.upper(),
        "summary": None,
        "research_area": None,
        "project_type": None,
        "platform": None,
        "environment": None,
        "hardware": None,
        "fuel_classes": [],
        "fuel_materials": [],
        "topic_tags": [],
        "measurement_types": [],
        "conditions": [],
        "files": [],
        "publications": [],
        "source_url": f"https://example.org/{record_id}",
        "doi": None,
        "source_updated_at": None,
        "ingested_at": "2026-11-14T00:00:00Z",
        "data_status": "verified",
    }
    return {**base, **fields}


def thin(record_id, title, acronym):
    """A record as the database holds it today: an empty source link and no other field."""
    return {"id": record_id, "source_id": record_id, "title": title, "acronym": acronym, "source_url": "", "data_status": "parsed"}


def condition(name, value, unit=None, context=None):
    citation = {"source_name": "made-up", "source_url": "https://example.org", "doi": None, "location": None, "accessed_at": "2026-11-14"}
    return {"name": name, "value": value, "unit": unit, "context": context, "citation": citation}


_row_numbers = itertools.count(1)


def row(record_id, **fields):
    """One test row of the contract. Every made-up row gets its own number."""
    number = next(_row_numbers)
    base = {
        "id": f"{record_id}-{number}",
        "investigation_id": record_id,
        "test_label": None,
        "fuel": None,
        "geometry": None,
        "oxygen_pct": None,
        "pressure_kpa": None,
        "flow_cm_s": None,
        "diluent": None,
        "outcome": None,
        "source_file": None,
        "source_row": number,
        "raw": {},
        "flags": [],
        "data_status": "verified",
    }
    return {**base, **fields}


def rows(record_id, field, values, **more):
    """One test row for each value of one field."""
    return [row(record_id, **{field: value}, **more) for value in values]


def use_data(monkeypatch, records=(), tests=(), topics=None, fuel_classes=None):
    """Give T5 made-up data through the functions of analytics/data.py."""
    records, tests = list(records), list(tests)
    monkeypatch.setattr(m.data, "records", lambda: records)
    monkeypatch.setattr(m.data, "tests", lambda: tests)
    monkeypatch.setattr(m.data, "topics", lambda: list(TOPICS if topics is None else topics))
    monkeypatch.setattr(m.data, "fuel_classes", lambda: list(FUELS if fuel_classes is None else fuel_classes))


# ---------- G: T5 uses no model, no database and no network ----------

T5_FILES = {"__init__.py", "data.py", "variables.py", "comparison.py", "coverage.py"}
# Every module that a T5 file may import. A new entry here is a decision, not a detail.
LOGIC_IMPORTS = {"__future__", "typing", "collections", "decimal", ".data", ".variables"}
ROUTE_IMPORTS = {"typing", "fastapi", "..analytics", "..schemas"}


def imported_modules(path):
    """The modules that a file imports: 'typing' for a library, '.data' and '..fixtures' for files of this app."""
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            dots = "." * node.level
            firsts = [node.module.split(".")[0]] if node.module else [alias.name for alias in node.names]
            modules.update(dots + first for first in firsts)
    return modules


def test_g1_a_t5_file_imports_only_what_the_plan_allows():
    # No model, no database and no network library is in the two lists. Only data.py may read the sample data.
    folder = BACKEND / "app" / "analytics"
    files = {path.name: path for path in folder.glob("*.py")}
    assert T5_FILES <= set(files)
    for name, path in files.items():
        # data.py reads the records and the test rows through the shared data file of the record routes,
        # and the two fixed lists from the sample data, as the filter route does.
        allowed = LOGIC_IMPORTS | ({"..fixtures", "..data_access"} if name == "data.py" else set())
        assert imported_modules(path) <= allowed, f"{name} imports {sorted(imported_modules(path) - allowed)}"
    for name in ("compare", "coverage", "variables"):
        modules = imported_modules(BACKEND / "app" / "routers" / f"{name}.py")
        assert modules <= ROUTE_IMPORTS, f"routers/{name}.py imports {sorted(modules - ROUTE_IMPORTS)}"


def test_g2_t5_changes_no_record_and_no_row_that_it_reads(monkeypatch):
    # These values invite a change in place: a number with rounding noise and a text with double spaces.
    tests = [*rows("x-a", "oxygen_pct", [0.14 * 100, 14]), row("x-b", fuel="1 cm   PMMA  film", oxygen_pct=14)]
    records = [record("x-a", topic_tags=["T1"], fuel_classes=["Gas"], conditions=[condition("Oxygen", 85.0, "% O2")]), record("x-b")]
    before = copy.deepcopy((records, tests))
    use_data(monkeypatch, records=records, tests=tests)
    assert [item["id"] for item in compare(["x-a", "x-b"])["investigations"]] == ["x-a", "x-b"]
    assert cell_ids(coverage(), "T1", "Gas") == ["x-a"]
    assert variables("x-a")["test_count"] == 2
    assert variables("x-b")["test_count"] == 1
    assert (records, tests) == before


# ---------- A: the compare table ----------


def test_a1_compare_gives_the_ten_rows_in_the_fixed_order():
    assert [item["field"] for item in compare(["psi-flex", "psi-bass-ii"])["rows"]] == ROW_NAMES


def test_a2_the_exact_cells_of_three_sample_records():
    body = compare(["psi-flex", "psi-bass-ii", "psi-acme-cfig"])
    assert body["investigations"] == [
        {"id": "psi-flex", "title": "Flame Extinguishment Experiment", "acronym": "FLEX", "source_url": PSI_HOME},
        {"id": "psi-bass-ii", "title": "Burning and Suppression of Solids - II", "acronym": "BASS-II", "source_url": PSI_HOME},
        {"id": "psi-acme-cfig", "title": "Cool Flames Investigation with Gases (ACME)", "acronym": "CFI-G", "source_url": PSI_HOME},
    ]
    assert table(body) == {
        "Research area": ["Combustion Science", "Combustion Science", "Combustion Science"],
        "Platform": ["International Space Station", "International Space Station", "International Space Station"],
        "Gravity environment": ["Microgravity", "Microgravity", "Microgravity"],
        "Hardware": [
            "Multi-user Droplet Combustion Apparatus (MDCA) in the Combustion Integrated Rack (CIR)",
            "Microgravity Science Glovebox (MSG), modular fan-driven flow duct built for SPICE",
            "Modular ACME hardware in the Combustion Integrated Rack (CIR)",
        ],
        "Fuel class": ["Liquid droplet", "Solid", "Gas"],
        "Fuels / materials": [None, "Fabrics, Plastics", "Propane (given as an example of the flammable gas)"],
        "Topics": [
            "Fire suppression, Droplet combustion",
            "Material flammability, Oxygen & airflow effects",
            "Oxygen & airflow effects, Flame structure",
        ],
        "Measurement types": ["Droplet burning observation", "Flame spread observation", None],
        "Reported conditions": [None, None, "Maximum oxygen concentration in oxidizer flow: 85 % O2"],
        "Linked files": ["1", None, None],
    }


def test_a3_the_text_forms_of_the_cells(monkeypatch):
    full = record(
        "x-a",
        research_area="Area A",
        fuel_classes=["Solid", "Gas"],
        fuel_materials=["PMMA"],
        topic_tags=["T1", "T2"],
        conditions=[
            condition("Oxygen", 85.0, "% O2"),
            condition("Flow", 21.5, "cm/s"),
            condition("Gap", 0.00005, "m"),
            condition("Igniter", "hot wire"),
            condition("Tests", 3),
        ],
        files=[{"id": "f1"}, {"id": "f2"}, {"id": "f3"}],
    )
    use_data(monkeypatch, records=[full, record("x-b")])
    assert table(compare(["x-a", "x-b"])) == {
        "Research area": ["Area A", None],
        "Platform": [None, None],
        "Gravity environment": [None, None],
        "Hardware": [None, None],
        "Fuel class": ["Solid, Gas", None],
        "Fuels / materials": ["PMMA", None],
        "Topics": ["T1, T2", None],
        "Measurement types": [None, None],
        "Reported conditions": ["Oxygen: 85 % O2, Flow: 21.5 cm/s, Gap: 0.00005 m, Igniter: hot wire, Tests: 3", None],
        "Linked files": ["3", None],
    }


def test_a4_a_missing_value_is_null_in_every_plain_row(monkeypatch):
    blank = record("x-a", research_area="", platform="   ", environment=None, hardware="Rig")
    use_data(monkeypatch, records=[blank, record("x-b", hardware="\t")])
    cells = table(compare(["x-a", "x-b"]))
    assert [cells[name] for name in ROW_NAMES[:4]] == [[None, None], [None, None], [None, None], ["Rig", None]]
    assert all(value not in ("", "0") for values in cells.values() for value in values)


def test_a5_the_record_list_follows_the_request(monkeypatch):
    use_data(monkeypatch, records=[record("x-a"), record("x-b", acronym=None, source_url="")])
    assert compare(["x-b", "x-a"])["investigations"] == [
        {"id": "x-b", "title": "Title of x-b", "acronym": None, "source_url": ""},
        {"id": "x-a", "title": "Title of x-a", "acronym": "X-A", "source_url": "https://example.org/x-a"},
    ]


def test_a7_a_repeated_id_counts_once():
    once = compare(["psi-flex", "psi-bass-ii"])
    assert [item["id"] for item in once["investigations"]] == ["psi-flex", "psi-bass-ii"]
    assert compare(["psi-flex", "psi-bass-ii", "psi-flex", "psi-bass-ii"]) == once
    assert compare(["psi-flex", "psi-bass-ii", "psi-flex"]) == once  # the first place of an id counts, not the last
    assert compare(["psi-flex"] * 4 + ["psi-bass-ii"]) == once  # a repeat does not count toward the limit of 4


def test_a8_an_unknown_record_is_left_out_and_a_note_says_so():
    body = compare(["psi-flex", "no-such-record", "psi-bass-ii", "another-one"])
    assert [item["id"] for item in body["investigations"]] == ["psi-flex", "psi-bass-ii"]
    assert body["notes"] == [STORED, CHARTS, ROW_CHARTS, TWO_MISSING, SAMPLE]
    repeated = compare(["psi-flex", "no-such-record", "psi-bass-ii", "no-such-record"])
    assert repeated["notes"] == [STORED, CHARTS, ROW_CHARTS, ONE_MISSING, SAMPLE]  # a repeated unknown id counts once

    one_left = compare(["psi-flex", "no-such-record"])  # the answer still shows what is left
    assert [item["id"] for item in one_left["investigations"]] == ["psi-flex"]
    assert [item["field"] for item in one_left["rows"]] == ROW_NAMES
    assert one_left["comparable_parameters"] == []
    assert one_left["notes"] == [STORED, CHARTS, ONE_MISSING, TOO_FEW, SAMPLE]

    assert compare(["no-such-record"]) == {**EMPTY_COMPARISON, "notes": [ONE_MISSING, TOO_FEW]}


def test_a9_only_the_first_four_records_are_used():
    body = compare(["psi-bass", "psi-bass-ii", "psi-saffire", "psi-same", "psi-same-r"])
    assert [item["id"] for item in body["investigations"]] == ["psi-bass", "psi-bass-ii", "psi-saffire", "psi-same"]
    assert body["notes"] == [STORED, CHARTS, FIRST_FOUR, SAMPLE]

    four_known = compare(["psi-bass", "no-such-record", "psi-bass-ii", "psi-saffire", "psi-same"])
    assert [item["id"] for item in four_known["investigations"]] == ["psi-bass", "psi-bass-ii", "psi-saffire", "psi-same"]
    assert four_known["notes"] == [STORED, CHARTS, ONE_MISSING, SAMPLE]

    both = compare(["psi-bass", "psi-bass-ii", "psi-saffire", "psi-same", "psi-same-r", "no-such-record"])
    assert [item["id"] for item in both["investigations"]] == ["psi-bass", "psi-bass-ii", "psi-saffire", "psi-same"]
    assert both["notes"] == [STORED, CHARTS, ONE_MISSING, FIRST_FOUR, SAMPLE]


def test_a9b_a_record_after_the_fourth_adds_nothing(monkeypatch):
    use_data(monkeypatch, records=[*(record(f"x-{letter}") for letter in "abcd"), record("x-e", data_status="parsed")])
    body = compare(["x-a", "x-b", "x-c", "x-d", "x-e"])
    assert [item["id"] for item in body["investigations"]] == ["x-a", "x-b", "x-c", "x-d"]
    assert body["notes"] == [STORED, CHARTS, FIRST_FOUR]  # the status of the fifth record does not count


def test_a10_an_empty_selection_gets_a_note_and_no_error():
    assert compare([]) == {**EMPTY_COMPARISON, "notes": [TOO_FEW]}


def test_a11_the_notes_say_when_no_person_checked_the_data(monkeypatch):
    checked = [record("x-a"), record("x-b")]
    use_data(monkeypatch, records=checked)
    assert compare(["x-a", "x-b"])["notes"] == [STORED, CHARTS]

    use_data(monkeypatch, records=[record("x-a"), record("x-b", data_status="parsed")])
    assert compare(["x-a", "x-b"])["notes"] == [STORED, CHARTS, PARSED]

    use_data(monkeypatch, records=[record("x-a", data_status="parsed"), record("x-b", data_status="sample")])
    assert compare(["x-a", "x-b"])["notes"] == [STORED, CHARTS, SAMPLE, PARSED]

    # A test row that no person checked counts too. A row of a record outside the comparison does not.
    use_data(monkeypatch, records=[*checked, record("x-c")], tests=[row("x-a", data_status="parsed"), row("x-c", data_status="sample")])
    body = compare(["x-a", "x-b"])
    assert [item["id"] for item in body["investigations"]] == ["x-a", "x-b"]
    assert body["notes"] == [STORED, CHARTS, PARSED]


@pytest.mark.parametrize("body", [{}, {"ids": ["psi-flex", "psi-bass-ii"]}, {"investigation_ids": "psi-flex"}, {"investigation_ids": None}])
def test_a12_a_malformed_request_still_gets_422(body):
    assert client.post(API + "/compare", json=body).status_code == 422


def test_a13_a_comparison_does_not_change_the_cached_sample_data():
    compare(["psi-flex", "psi-bass-ii", "psi-acme-cfig", "psi-same"])
    compare(["psi-flex", "no-such-record"])
    assert sample_data_is_unchanged()


def test_a14_records_as_the_database_holds_them_today(monkeypatch):
    thin_records = [thin("PSI-25", "Burning and Suppression of Solids - II (BASS-II)", "BASS-II"), thin("PSI-69", "Flame Extinguishment Experiment (FLEX)", "FLEX")]
    use_data(monkeypatch, records=thin_records)
    body = compare(["PSI-69", "PSI-25"])
    assert body["investigations"] == [
        {"id": "PSI-69", "title": "Flame Extinguishment Experiment (FLEX)", "acronym": "FLEX", "source_url": ""},
        {"id": "PSI-25", "title": "Burning and Suppression of Solids - II (BASS-II)", "acronym": "BASS-II", "source_url": ""},
    ]
    assert table(body) == {name: [None, None] for name in ROW_NAMES}
    assert body["comparable_parameters"] == []
    assert body["notes"] == [STORED, CHARTS, PARSED]


# ---------- B: the comparable numbers of the charts ----------

OXYGEN = ("Oxygen concentration", "% by volume")


def test_b1_two_records_with_the_same_name_and_unit_give_one_chart(monkeypatch):
    first = record("x-a", acronym="ALPHA", conditions=[condition(OXYGEN[0], 21, OXYGEN[1]), condition("Igniter", "hot wire")])
    second = record("x-b", acronym=None, title="Bravo study", conditions=[condition(OXYGEN[0], 30.5, OXYGEN[1])])
    use_data(monkeypatch, records=[first, second])
    body = compare(["x-a", "x-b"])
    assert charts(body) == [(*OXYGEN, [("x-a", "ALPHA", 21.0), ("x-b", "Bravo study", 30.5)])]
    assert body["notes"] == [STORED, CHARTS]  # the note about test rows is for charts of test rows only
    assert charts(compare(["x-b", "x-a"])) == [(*OXYGEN, [("x-b", "Bravo study", 30.5), ("x-a", "ALPHA", 21.0)])]


@pytest.mark.parametrize(
    "other",
    [
        condition(OXYGEN[0], 30, "kPa"),
        condition("Oxygen level", 30, OXYGEN[1]),
        condition("oxygen concentration", 30, OXYGEN[1]),
        condition(OXYGEN[0], "30", OXYGEN[1]),
        condition(OXYGEN[0], True, OXYGEN[1]),
        None,
    ],
    ids=["other unit", "other name", "capital letter", "text value", "true", "one record only"],
)
def test_b2_values_that_are_not_comparable_give_no_chart(monkeypatch, other):
    first = record("x-a", conditions=[condition(OXYGEN[0], 21, OXYGEN[1])])
    second = record("x-b", conditions=[other] if other else [])
    use_data(monkeypatch, records=[first, second])
    body = compare(["x-a", "x-b"])
    assert [item["id"] for item in body["investigations"]] == ["x-a", "x-b"]
    assert body["comparable_parameters"] == []
    assert body["notes"] == [STORED, CHARTS]


@pytest.mark.parametrize("unit", [None, "", "  "], ids=["none", "empty", "blank"])
def test_b2b_a_number_with_no_unit_gives_no_chart(monkeypatch, unit):
    # Both records have the same name and the same missing unit, so only the unit rule can stop the chart.
    both = [record("x-a", conditions=[condition(OXYGEN[0], 21, unit)]), record("x-b", conditions=[condition(OXYGEN[0], 30, unit)])]
    use_data(monkeypatch, records=both)
    body = compare(["x-a", "x-b"])
    assert table(body)["Reported conditions"] == ["Oxygen concentration: 21", "Oxygen concentration: 30"]
    assert body["comparable_parameters"] == []


def test_b3_one_record_that_reports_a_pair_twice(monkeypatch):
    twice = record("x-a", acronym="ALPHA", conditions=[condition(OXYGEN[0], 10, OXYGEN[1], "at the start"), condition(OXYGEN[0], 20, OXYGEN[1], "at the end")])
    use_data(monkeypatch, records=[twice, record("x-b"), record("x-c", acronym="CHARLIE", conditions=[condition(OXYGEN[0], 30, OXYGEN[1])])])
    alone = compare(["x-a", "x-b"])
    assert [item["id"] for item in alone["investigations"]] == ["x-a", "x-b"]
    assert alone["comparable_parameters"] == []  # two values of one record are no comparison
    assert charts(compare(["x-a", "x-c"])) == [(*OXYGEN, [("x-a", "ALPHA (1)", 10.0), ("x-a", "ALPHA (2)", 20.0), ("x-c", "CHARLIE", 30.0)])]


def test_b4_the_test_rows_give_the_lowest_and_the_highest_value(monkeypatch):
    tests = [
        *rows("x-a", "oxygen_pct", [21, 30, None, 25]),
        row("x-a", pressure_kpa=101.3),
        *rows("x-b", "oxygen_pct", [25, 18]),
        *rows("x-c", "oxygen_pct", [None, None]),
    ]
    use_data(monkeypatch, records=[record("x-a"), record("x-b"), record("x-c")], tests=tests)
    body = compare(["x-a", "x-b", "x-c"])
    assert charts(body) == [
        ("Oxygen, lowest value in the test rows", "% by volume", [("x-a", "X-A", 21.0), ("x-b", "X-B", 18.0)]),
        ("Oxygen, highest value in the test rows", "% by volume", [("x-a", "X-A", 30.0), ("x-b", "X-B", 25.0)]),
    ]  # the pressure has one record only, and x-c reports no value
    assert body["notes"] == [STORED, CHARTS, ROW_CHARTS]
    assert compare(["x-a", "x-c"])["comparable_parameters"] == []


def test_b5_one_single_value_in_every_record_gives_one_chart(monkeypatch):
    tests = [*rows("x-a", "oxygen_pct", [14, 14.0]), *rows("x-b", "oxygen_pct", [0.14 * 100, 14]), *rows("x-b", "flow_cm_s", [5.5]), *rows("x-a", "flow_cm_s", [7])]
    use_data(monkeypatch, records=[record("x-a"), record("x-b")], tests=tests)
    assert 0.14 * 100 != 14  # the noise that the rounding removes
    assert charts(compare(["x-a", "x-b"])) == [
        ("Oxygen in the test rows", "% by volume", [("x-a", "X-A", 14.0), ("x-b", "X-B", 14.0)]),
        ("Flow in the test rows", "cm/s", [("x-a", "X-A", 7.0), ("x-b", "X-B", 5.5)]),
    ]


def test_b6_flex_and_bass_ii_get_one_oxygen_chart_from_the_sample_rows():
    body = compare(["psi-flex", "psi-bass-ii"])
    assert charts(body) == [("Oxygen in the test rows", "% by volume", [("psi-flex", "FLEX", 21.0), ("psi-bass-ii", "BASS-II", 22.2)])]
    assert body["notes"] == [STORED, CHARTS, ROW_CHARTS, SAMPLE]


def test_b7_the_order_of_the_charts(monkeypatch):
    shared = [condition("Zeta", 1, "s"), condition("Alpha", 2, "m")]
    tests = []
    for record_id, shift in (("x-a", 0), ("x-b", 1)):
        tests += rows(record_id, "flow_cm_s", [5 + shift, 9 + shift])
        tests += rows(record_id, "pressure_kpa", [50 + shift, 90 + shift])
        tests += rows(record_id, "oxygen_pct", [15 + shift, 19 + shift])
    use_data(monkeypatch, records=[record("x-a", conditions=shared), record("x-b", conditions=shared)], tests=tests)
    body = compare(["x-a", "x-b"])
    assert [(name, unit) for name, unit, _ in charts(body)] == [
        ("Zeta", "s"),
        ("Alpha", "m"),
        ("Oxygen, lowest value in the test rows", "% by volume"),
        ("Oxygen, highest value in the test rows", "% by volume"),
        ("Pressure, lowest value in the test rows", "kPa"),
        ("Pressure, highest value in the test rows", "kPa"),
        ("Flow, lowest value in the test rows", "cm/s"),
        ("Flow, highest value in the test rows", "cm/s"),
    ]
    assert charts(body)[4][2] == [("x-a", "X-A", 50.0), ("x-b", "X-B", 51.0)]


def test_b8_two_sample_records_with_no_shared_number_get_no_chart():
    body = compare(["psi-bass", "psi-same"])
    assert body["comparable_parameters"] == []
    assert body["notes"] == [STORED, CHARTS, SAMPLE]


def test_b9_the_values_follow_the_order_of_the_records(monkeypatch):
    tests = [*rows("x-d", "oxygen_pct", [40]), *rows("x-a", "oxygen_pct", [10]), *rows("x-c", "oxygen_pct", [30])]
    records = [record("x-a"), record("x-b"), record("x-c", acronym=None, title="Charlie study"), record("x-d")]
    use_data(monkeypatch, records=records, tests=tests)
    assert charts(compare(["x-c", "x-b", "x-d", "x-a"])) == [
        ("Oxygen in the test rows", "% by volume", [("x-c", "Charlie study", 30.0), ("x-d", "X-D", 40.0), ("x-a", "X-A", 10.0)])
    ]  # x-b has no test row, and a record with no acronym shows its title


def test_b10_zero_is_a_reported_value(monkeypatch):
    tests = [*rows("x-a", "flow_cm_s", [0, 0]), *rows("x-b", "flow_cm_s", [0.0])]
    records = [record("x-a", conditions=[condition("Flow", 0, "cm/s")]), record("x-b", conditions=[condition("Flow", 0.0, "cm/s")])]
    use_data(monkeypatch, records=records, tests=tests)
    body = compare(["x-a", "x-b"])
    assert table(body)["Reported conditions"] == ["Flow: 0 cm/s", "Flow: 0 cm/s"]
    assert charts(body) == [
        ("Flow", "cm/s", [("x-a", "X-A", 0.0), ("x-b", "X-B", 0.0)]),
        ("Flow in the test rows", "cm/s", [("x-a", "X-A", 0.0), ("x-b", "X-B", 0.0)]),
    ]


def test_b11_one_record_varies_and_one_does_not(monkeypatch):
    tests = [*rows("x-a", "oxygen_pct", [21, 30]), *rows("x-b", "oxygen_pct", [21, 21])]
    use_data(monkeypatch, records=[record("x-a"), record("x-b")], tests=tests)
    assert charts(compare(["x-a", "x-b"])) == [
        ("Oxygen, lowest value in the test rows", "% by volume", [("x-a", "X-A", 21.0), ("x-b", "X-B", 21.0)]),
        ("Oxygen, highest value in the test rows", "% by volume", [("x-a", "X-A", 30.0), ("x-b", "X-B", 21.0)]),
    ]  # one chart only when every record has a single value


def test_b12_two_records_with_the_same_acronym_keep_it_as_their_label(monkeypatch):
    tests = [*rows("x-a", "oxygen_pct", [21]), *rows("x-b", "oxygen_pct", [30])]
    use_data(monkeypatch, records=[record("x-a", acronym="ACME"), record("x-b", acronym="ACME")], tests=tests)
    assert charts(compare(["x-a", "x-b"])) == [("Oxygen in the test rows", "% by volume", [("x-a", "ACME", 21.0), ("x-b", "ACME", 30.0)])]


# ---------- C: the coverage matrix ----------


def test_c1_the_matrix_of_the_sample_data():
    body = coverage()
    assert (body["row_dimension"], body["column_dimension"]) == ("Research topic", "Fuel / material class")
    assert body["rows"] == [
        "Material flammability",
        "Fire suppression",
        "Smoke & aerosol detection",
        "Flame structure",
        "Oxygen & airflow effects",
        "Droplet combustion",
        "Electric-field effects",
    ]
    assert body["columns"] == ["Solid", "Gas", "Liquid droplet", "Particulate / aerosol"]
    assert counts(body) == [[3, 1, 0, 0], [0, 0, 2, 0], [0, 0, 0, 3], [1, 4, 0, 0], [3, 2, 0, 0], [0, 0, 3, 0], [0, 1, 0, 0]]
    assert cell_ids(body, "Fire suppression", "Liquid droplet") == ["psi-flex", "psi-flex-2"]


def test_c2_a_record_counts_in_each_cell_that_matches(monkeypatch):
    both = record("x-a", topic_tags=["T1", "T2"], fuel_classes=["Solid", "Gas"])
    use_data(monkeypatch, records=[record("x-b", topic_tags=["T2"], fuel_classes=["Gas"]), both])
    body = coverage()
    assert (body["rows"], body["columns"]) == (TOPICS, FUELS)
    assert counts(body) == [[1, 1], [1, 2], [0, 0]]
    assert cell_ids(body, "T2", "Gas") == ["x-b", "x-a"]  # the order of the records
    assert cell_ids(body, "T1", "Solid") == ["x-a"]


def test_c3_a_topic_or_fuel_class_outside_the_lists_adds_no_row_and_no_column(monkeypatch):
    listed_too = record("x-a", topic_tags=["Unlisted topic", "T1"], fuel_classes=["Solid", "Unlisted fuel"])
    unlisted_topic = record("x-b", topic_tags=["Unlisted topic"], fuel_classes=["Solid"])
    unlisted_fuel = record("x-c", topic_tags=["T1"], fuel_classes=["Unlisted fuel"])
    unlisted_both = record("x-d", topic_tags=["Unlisted topic"], fuel_classes=["Unlisted fuel"])
    use_data(monkeypatch, records=[listed_too, unlisted_topic, unlisted_fuel, unlisted_both])
    first, second = coverage(), coverage()
    assert first == second
    assert (first["rows"], first["columns"]) == (TOPICS, FUELS)  # the lists of the Explore filters, not longer
    assert counts(first) == [[1, 0], [0, 0], [0, 0]]
    assert cell_ids(first, "T1", "Solid") == ["x-a"]
    assert first["method_notes"] == [COUNT, MULTI, GAP, THREE_UNPLACED]  # x-b, x-c and x-d are in no cell


def test_c4_a_note_counts_the_records_that_the_map_cannot_place(monkeypatch):
    placed = record("x-a", topic_tags=["T1"], fuel_classes=["Gas"])
    no_topic = record("x-b", fuel_classes=["Gas"])
    no_fuel = record("x-c", topic_tags=["T1"])
    nothing = record("x-d")

    use_data(monkeypatch, records=[placed])
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP]

    use_data(monkeypatch, records=[placed, no_topic])
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, ONE_UNPLACED]

    use_data(monkeypatch, records=[no_topic, placed, no_fuel, nothing])
    body = coverage()
    assert body["method_notes"] == [COUNT, MULTI, GAP, THREE_UNPLACED]
    assert counts(body) == [[0, 1], [0, 0], [0, 0]]
    assert cell_ids(body, "T1", "Gas") == ["x-a"]


def test_c5_the_notes_say_when_no_person_checked_the_counted_records(monkeypatch):
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, SAMPLE]  # the sample data

    placed = {"topic_tags": ["T1"], "fuel_classes": ["Gas"]}
    use_data(monkeypatch, records=[record("x-a", **placed), record("x-b", data_status="parsed", **placed)])
    assert cell_ids(coverage(), "T1", "Gas") == ["x-a", "x-b"]
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, PARSED]

    use_data(monkeypatch, records=[record("x-a", data_status="parsed", **placed), record("x-b", data_status="sample", **placed)])
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, SAMPLE, PARSED]

    # A record that the map cannot place is not counted, so its status adds no note.
    use_data(monkeypatch, records=[record("x-a", **placed), record("x-b", data_status="sample")])
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, ONE_UNPLACED]

    use_data(monkeypatch, records=[record("x-a", data_status="sample", **placed), record("x-b")])
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, ONE_UNPLACED, SAMPLE]  # the order of the two notes


def test_c6_coverage_does_not_change_the_cached_sample_data():
    assert coverage() == coverage()
    assert sample_data_is_unchanged()


def test_c7_no_record_at_all(monkeypatch):
    use_data(monkeypatch)
    body = coverage()
    assert (body["rows"], body["columns"]) == (TOPICS, FUELS)
    assert counts(body) == [[0, 0], [0, 0], [0, 0]]
    assert body["method_notes"] == [COUNT, MULTI, GAP]


def test_c8_records_as_the_database_holds_them_today(monkeypatch):
    thin_records = [thin("PSI-25", "BASS-II", "BASS-II"), thin("PSI-69", "FLEX", "FLEX"), thin("PSI-68", "FLEX-2", "FLEX-2")]
    use_data(monkeypatch, records=thin_records)
    body = coverage()
    assert counts(body) == [[0, 0], [0, 0], [0, 0]]
    assert body["method_notes"] == [COUNT, MULTI, GAP, THREE_UNPLACED]


# ---------- D: the variables of one record ----------


@pytest.mark.parametrize(
    "field, values, expected",
    [
        ("fuel", [None, None], var("fuel", "not_reported")),
        ("fuel", ["PMMA", "PMMA"], var("fuel", "constant", ["PMMA"])),
        ("fuel", ["PMMA", "Nomex"], var("fuel", "varied", ["PMMA", "Nomex"])),
        ("outcome", ["", "  "], var("outcome", "not_reported")),
        ("flow_cm_s", [None, None], var("flow_cm_s", "not_reported")),
        ("flow_cm_s", [5, 5.0], var("flow_cm_s", "constant", ["5"], 5.0, 5.0)),
        ("flow_cm_s", [10, 5], var("flow_cm_s", "varied", ["5", "10"], 5.0, 10.0)),
        ("flow_cm_s", [0, 0.0], var("flow_cm_s", "constant", ["0"], 0.0, 0.0)),  # zero is a reported value
        ("flow_cm_s", [True, True], var("flow_cm_s", "not_reported")),  # true is not a number
    ],
)
def test_d1_a_field_is_not_reported_constant_or_varied(monkeypatch, field, values, expected):
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", field, values))
    body = variables("x-a")
    assert body["test_count"] == 2
    assert entry(body, field) == expected
    assert body["notes"] == []


def test_d2_a_note_names_a_field_that_some_tests_do_not_report(monkeypatch):
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "pressure_kpa", [101.3, None, 70]))
    body = variables("x-a")
    assert entry(body, "pressure_kpa") == var("pressure_kpa", "varied", ["70", "101.3"], 70.0, 101.3)
    assert body["notes"] == ["1 of 3 tests does not report pressure_kpa."]  # no note for the 6 fields that no test reports

    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "outcome", ["Extinction", None, ""]))
    body = variables("x-a")
    assert entry(body, "outcome") == var("outcome", "constant", ["Extinction"])
    assert body["notes"] == ["2 of 3 tests do not report outcome."]

    # Several notes: one field after the other in the fixed order, and the note about unchecked data last.
    tests = [
        row("x-a", fuel=("PMMA" if number > 1 else None), oxygen_pct=(number if number < 14 else None), outcome=("Out" if number != 2 else None), data_status="sample")
        for number in range(1, 15)
    ]
    use_data(monkeypatch, records=[record("x-a")], tests=tests)
    assert variables("x-a")["notes"] == [
        "1 of 14 tests does not report fuel.",
        "1 of 14 tests does not report oxygen_pct.",
        "oxygen_pct has 13 different values. They are not listed.",
        "1 of 14 tests does not report outcome.",
        SAMPLE,
    ]


def test_d3_a_number_field_gets_its_lowest_and_highest_value(monkeypatch):
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "oxygen_pct", [30, 21.0, 21.0, 25.5]))
    assert entry(variables("x-a"), "oxygen_pct") == var("oxygen_pct", "varied", ["21", "25.5", "30"], 21.0, 30.0)

    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "oxygen_pct", [14, 0.14 * 100]))
    assert entry(variables("x-a"), "oxygen_pct") == var("oxygen_pct", "constant", ["14"], 14.0, 14.0)

    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "oxygen_pct", list(range(12, 0, -1))))
    body = variables("x-a")
    assert entry(body, "oxygen_pct") == var("oxygen_pct", "varied", [str(number) for number in range(1, 13)], 1.0, 12.0)
    assert body["notes"] == []

    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "oxygen_pct", list(range(13, 0, -1))))
    body = variables("x-a")
    assert entry(body, "oxygen_pct") == var("oxygen_pct", "varied", [], 1.0, 13.0)
    assert body["notes"] == ["oxygen_pct has 13 different values. They are not listed."]

    # Six decimal places, not fewer, and a plain decimal for a very small and a very large number.
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "oxygen_pct", [21.1234561, 21.1234564, 21.123457]))
    assert entry(variables("x-a"), "oxygen_pct") == var("oxygen_pct", "varied", ["21.123456", "21.123457"], 21.123456, 21.123457)
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "pressure_kpa", [0.00005, 101.018298, 1234567.5]))
    assert entry(variables("x-a"), "pressure_kpa") == var("pressure_kpa", "varied", ["0.00005", "101.018298", "1234567.5"], 0.00005, 1234567.5)


def test_d4_a_text_field_shows_each_value_once(monkeypatch):
    spellings = ["Methanol", "methanol ", "  METHANOL", "Heptane", "1 cm   PMMA  film", "1 cm PMMA film"]
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "fuel", spellings))
    assert entry(variables("x-a"), "fuel") == var("fuel", "varied", ["Methanol", "Heptane", "1 cm PMMA film"])

    names = [f"F{number:02d}" for number in range(13, 0, -1)]  # F13 down to F01: the first appearance is not the alphabet
    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "fuel", [*names[:12], names[0]]))
    body = variables("x-a")
    assert entry(body, "fuel") == var("fuel", "varied", names[:12])  # exactly 12 values: all are listed
    assert body["notes"] == []

    use_data(monkeypatch, records=[record("x-a")], tests=rows("x-a", "fuel", [*names, names[5], names[9], names[9]]))
    body = variables("x-a")  # 13 values: F04 three times, F08 twice, the others once
    assert entry(body, "fuel") == var("fuel", "varied", ["F04", "F08", *names[:5], *names[6:9], *names[10:12]])  # F01 is left out
    assert body["notes"] == ["fuel has 13 different values. The 12 most frequent are shown."]


def test_d5_the_shape_of_the_answer():
    body = variables("psi-flex")
    assert body["test_count"] == 3
    assert [item["field"] for item in body["variables"]] == FIELDS


def test_d6_a_record_with_no_test_row_and_an_unknown_record():
    assert variables("psi-bass") == {"investigation_id": "psi-bass", "test_count": 0, "variables": [], "notes": [NO_ROWS]}
    response = client.get(API + "/investigations/no-such-record/variables")
    assert response.status_code == 404
    assert response.json() == {"detail": 'Investigation "no-such-record" was not found in the indexed records.'}


def test_d7_the_exact_answer_for_flex_on_the_sample_rows():
    assert variables("psi-flex") == {
        "investigation_id": "psi-flex",
        "test_count": 3,
        "variables": [
            var("fuel", "constant", ["Methanol"]),
            var("geometry", "not_reported"),
            var("oxygen_pct", "constant", ["21"], 21.0, 21.0),
            var("pressure_kpa", "varied", ["101.02", "101.59", "101.88"], 101.02, 101.88),
            var("flow_cm_s", "not_reported"),
            var("diluent", "not_reported"),
            var("outcome", "varied", ["Disruption", "Extinction"]),
        ],
        "notes": [SAMPLE],
    }


def test_d8_the_exact_answer_for_bass_ii_on_the_sample_rows():
    assert variables("psi-bass-ii") == {
        "investigation_id": "psi-bass-ii",
        "test_count": 3,
        "variables": [
            var("fuel", "varied", ["100 micron PMMA film 2 cm wide", "100 micron film 2 cm wide", "300 micron PMMA film 2 cm wide"]),
            var("geometry", "not_reported"),
            var("oxygen_pct", "constant", ["22.2"], 22.2, 22.2),
            var("pressure_kpa", "not_reported"),
            var("flow_cm_s", "not_reported"),
            var("diluent", "not_reported"),
            var("outcome", "not_reported"),
        ],
        "notes": [SAMPLE],
    }


def test_d9_bass_ii_rows_as_they_really_are(monkeypatch):
    # The fan value is a dial setting. The ingest keeps it in the raw column only, and flow_cm_s stays empty.
    warning = "flow_cm_s: 'Fan display' is a dimensionless dial setting, not cm/s; kept raw value, set flow_cm_s to null"
    first = row("PSI-25", fuel="PMMA film", oxygen_pct=22.2, raw={"Fan display": "62", "Flow restrictor": "2"}, flags=[warning], data_status="parsed")
    second = row("PSI-25", fuel="PMMA film", oxygen_pct=17.5, raw={"Fan display": "47", "Flow restrictor": "2"}, data_status="parsed")
    del second["flags"]  # some stored rows have no list of warnings
    use_data(monkeypatch, records=[thin("PSI-25", "Burning and Suppression of Solids - II (BASS-II)", "BASS-II")], tests=[first, second])
    body = variables("PSI-25")
    assert body["test_count"] == 2
    assert [item["field"] for item in body["variables"]] == FIELDS  # the contract fields only, no raw column
    assert entry(body, "flow_cm_s") == var("flow_cm_s", "not_reported")
    assert entry(body, "oxygen_pct") == var("oxygen_pct", "varied", ["17.5", "22.2"], 17.5, 22.2)
    assert body["notes"] == [PARSED]


def test_d10_the_variables_answer_does_not_change_the_cached_sample_data():
    assert variables("psi-flex") == variables("psi-flex")
    variables("psi-bass-ii")
    assert sample_data_is_unchanged()


@pytest.mark.parametrize(
    "statuses, notes",
    [(["verified", "verified"], []), (["sample", "verified"], [SAMPLE]), (["verified", "parsed"], [PARSED]), (["parsed", "sample"], [SAMPLE, PARSED])],
)
def test_d11_the_notes_say_when_no_person_checked_the_rows(monkeypatch, statuses, notes):
    tests = [row("x-a", fuel="PMMA", data_status=status) for status in statuses]
    use_data(monkeypatch, records=[record("x-a", data_status="sample")], tests=tests)  # the status of the rows counts
    body = variables("x-a")
    assert entry(body, "fuel") == var("fuel", "constant", ["PMMA"])
    assert body["notes"] == notes


# ---------- N: T5 reads through the shared data file of the record routes (app/data_access.py) ----------


def shared_file(monkeypatch, records=(), tests=(), fail=False):
    """Stand in for the two functions of app/data_access.py that T5 calls. Returns the list of calls.

    Like the database, the stand-in gives at most 1,000 records for one call.
    """
    calls = []
    records, tests = list(records), list(tests)

    def list_investigations(q=None, hardware_family=None, page=1, page_size=25):
        calls.append(("records", q, hardware_family, page, page_size))
        if fail:
            raise HTTPException(status_code=503, detail="Database query failed: made-up")
        start = (page - 1) * page_size
        return copy.deepcopy(records[start : start + min(page_size, 1000)]), len(records), "supabase"

    def iter_tests_csv(investigation_id=None):
        calls.append(("tests", investigation_id))
        if fail:
            raise HTTPException(status_code=503, detail="Database query failed: made-up")
        return iter(copy.deepcopy([item for item in tests if investigation_id in (None, item["investigation_id"])])), "supabase"

    monkeypatch.setattr(data_access, "list_investigations", list_investigations)
    monkeypatch.setattr(data_access, "iter_tests_csv", iter_tests_csv)
    return calls


def test_n1_the_records_come_from_the_shared_data_file(monkeypatch):
    many = [record(f"x-{number:04d}") for number in range(2300)]
    calls = shared_file(monkeypatch, records=many)
    assert [item["id"] for item in m.data.records()] == [item["id"] for item in many]  # every record once
    assert len(calls) == 3  # pages of at most 1,000
    assert all(call[:3] == ("records", None, None) for call in calls)  # no search text and no filter

    calls = shared_file(monkeypatch, records=many[:2000])
    assert len(m.data.records()) == 2000 and len(calls) == 2


def test_n2_the_test_rows_come_from_the_shared_data_file(monkeypatch):
    stored = [row("x-a", oxygen_pct=21), row("x-b", oxygen_pct=30), row("x-a", oxygen_pct=25)]
    calls = shared_file(monkeypatch, tests=stored)
    assert m.data.tests() == stored
    assert calls == [("tests", None)]


def test_n3_a_database_error_is_not_hidden_behind_sample_data(monkeypatch):
    shared_file(monkeypatch, fail=True)
    assert client.post(API + "/compare", json={"investigation_ids": ["psi-flex", "psi-bass-ii"]}).status_code == 503
    assert client.get(API + "/analytics/coverage").status_code == 503
    assert client.get(API + "/investigations/psi-flex/variables").status_code == 503


def test_n4_database_records_and_rows_reach_the_three_answers(monkeypatch):
    stored = [
        thin("PSI-25", "Burning and Suppression of Solids - II (BASS-II)", "BASS-II"),
        thin("PSI-68", "Flame Extinguishment Experiment - 2 (FLEX-2)", "FLEX-2"),
        thin("PSI-69", "Flame Extinguishment Experiment (FLEX)", "FLEX"),
    ]
    tests = [*rows("PSI-25", "oxygen_pct", [13.6, 22.2], data_status="parsed"), *rows("PSI-69", "oxygen_pct", [12, 34], data_status="parsed")]
    shared_file(monkeypatch, records=stored, tests=tests)

    body = compare(["PSI-69", "PSI-25"])  # the ids that the Explore page gives with the database
    assert [item["id"] for item in body["investigations"]] == ["PSI-69", "PSI-25"]
    assert charts(body) == [
        ("Oxygen, lowest value in the test rows", "% by volume", [("PSI-69", "FLEX", 12.0), ("PSI-25", "BASS-II", 13.6)]),
        ("Oxygen, highest value in the test rows", "% by volume", [("PSI-69", "FLEX", 34.0), ("PSI-25", "BASS-II", 22.2)]),
    ]
    answer = variables("PSI-69")
    assert answer["test_count"] == 2
    assert entry(answer, "oxygen_pct") == var("oxygen_pct", "varied", ["12", "34"], 12.0, 34.0)
    assert coverage()["method_notes"] == [COUNT, MULTI, GAP, THREE_UNPLACED]
    assert client.get(API + "/investigations/psi-flex/variables").status_code == 404  # a sample id is no database record


# ---------- E: agreement with the other routes (over HTTP, no code of another task is imported) ----------


def record_ids(**filters):
    response = client.get(API + "/investigations", params={"page_size": 100, **filters})
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == len(page["items"]), "more records than one page"
    return [item["id"] for item in page["items"]]


def test_e1_the_matrix_uses_the_lists_of_the_explore_filters():
    options = client.get(API + "/filters").json()
    body = coverage()
    assert (body["rows"], body["columns"]) == (options["topics"], options["materials"])


def test_e2_the_variables_route_knows_the_same_records_as_the_record_route():
    for record_id in record_ids():
        variables(record_id)
    unknown = client.get(API + "/investigations/no-such-record")
    assert unknown.status_code == 404
    assert client.get(API + "/investigations/no-such-record/variables").json() == unknown.json()


def test_e3_every_record_in_a_t5_answer_is_a_record_of_the_record_route():
    known = record_ids()
    # Every sample record has a listed topic and a listed fuel class, so the map shows all of them.
    assert {record_id for cell in coverage()["cells"] for record_id in cell["investigation_ids"]} == set(known)
    assert [item["id"] for item in compare(known[:4])["investigations"]] == known[:4]


@pytest.mark.xfail(reason="the record route ignores the filters until task T3 adds them", strict=False)
def test_e4_a_cell_of_the_matrix_links_to_the_same_records_in_explore():
    for cell in coverage()["cells"]:
        if cell["count"]:
            assert record_ids(topic=cell["row"], material=cell["column"]) == cell["investigation_ids"]
