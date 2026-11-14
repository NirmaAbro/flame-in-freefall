"""T6 checks: the AI mapping assistant (backend/ai/mapping).

The test numbers are the ones in the T6 plan. Tests 1 to 4, 36 and 43 are in
test_mapping_shapes.py. Tests 25 and 27 are the existing checks in test_stubs.py.

Every test here writes to a temporary folder and uses a fake model. Only test 24
calls the real model, and it is skipped without LLM_API_KEY.

Run from the backend folder:  python -m pytest
"""
import csv
import importlib
import inspect
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app import llm, schemas

BACKEND = Path(__file__).resolve().parents[1]
REPO_DATA = BACKEND.parent / "data"
FIXED_TIME = datetime(2026, 11, 14, 15, 0, 0, tzinfo=timezone.utc)
IGNORED_FOLDERS = {".venv", "__pycache__", ".pytest_cache"}


class _Modules:
    """ai.mapping.<name>, imported on first use, so each test fails on its own before the code exists."""

    def __getattr__(self, name):
        return importlib.import_module(f"ai.mapping.{name}")


m = _Modules()


def now():
    return FIXED_TIME


# ---------- Guards (test 38) ----------


def snapshot(folder: Path):
    """Every file and folder under a folder, with file sizes and change times."""
    seen = {}
    for path in sorted(folder.rglob("*")):
        if IGNORED_FOLDERS.intersection(path.relative_to(folder).parts):
            continue
        stat = path.stat()
        seen[str(path.relative_to(folder))] = "folder" if path.is_dir() else (stat.st_size, stat.st_mtime_ns)
    return seen


def repo_state():
    return {"data": snapshot(REPO_DATA), "backend": snapshot(BACKEND)}


@pytest.fixture(scope="module", autouse=True)
def repo_is_untouched():
    """Runs around the whole file, also when a run stops early or selects a few tests."""
    before = repo_state()
    yield before
    assert repo_state() == before, "a test changed a real file of the repo"


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    if "live" in request.keywords:
        return

    def blocked_post(*args, **kwargs):
        raise AssertionError("a test tried to reach the network")

    def blocked_connect(self, address):
        raise OSError(f"a test tried to open a network connection to {address!r}")

    monkeypatch.setattr(httpx, "post", blocked_post)
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)


@pytest.fixture(autouse=True)
def no_real_keys(request, monkeypatch):
    if "live" in request.keywords:
        return
    for name in ("LLM_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        monkeypatch.delenv(name, raising=False)


# ---------- Small copies of two real PSI tables ----------


def sample_rows(investigation_id):
    rows = json.loads((BACKEND / "fixtures" / "tests.json").read_text(encoding="utf-8"))
    return [row["raw"] for row in rows if row["investigation_id"] == investigation_id]


BASS_ROWS = sample_rows("psi-bass-ii")
FLEX_ROWS = sample_rows("psi-flex")
BASS_HEADER = list(BASS_ROWS[0])
FLEX_HEADER = list(FLEX_ROWS[0])

BASS_FILE = "PSI-25_Experimental table_BASS-II.csv"  # the real file name, with its space
FLEX_FILE = "PSI-69_Experimental table_FLEX.csv"

BASS_GOOD = {
    "Test #": ("test_label", None),
    "Fuel Sample Material": ("fuel", None),
    "Calibrated initial O2 % by vol": ("oxygen_pct", "percent"),
}
FLEX_GOOD = {
    "FLEX Identifier": ("test_label", None),
    "Fuel": ("fuel", None),
    "Ambient pressure; mmHg": ("pressure_kpa", "mmHg"),
    "O initial ambient composition; mole fraction": ("oxygen_pct", "mole_fraction"),
    "Test end": ("outcome", None),
}
FAN_WARNING = "unit_not_in_column_name:Fan display"


def write_table(data_dir: Path, file_name, header, rows, encoding="utf-8"):
    raw = data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / file_name
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(name, "") for name in header])
    return path


@pytest.fixture
def data_dir(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    return folder


@pytest.fixture
def bass(data_dir):
    return write_table(data_dir, BASS_FILE, BASS_HEADER, BASS_ROWS)


@pytest.fixture
def flex(data_dir):
    return write_table(data_dir, FLEX_FILE, FLEX_HEADER, FLEX_ROWS)


def columns_for(header, mapped):
    return [
        {
            "source_column": name,
            "target_field": mapped.get(name, (None, None))[0],
            "unit": mapped.get(name, (None, None))[1],
            "confidence": "high",
            "note": None,
        }
        for name in header
    ]


def answer_for(header, mapped):
    """What a well-behaved model returns: only the list of columns."""
    return json.dumps({"columns": columns_for(header, mapped)})


def mapping_dict(header, mapped, source_id="PSI-25", source_file=BASS_FILE, **changes):
    base = {
        "source_id": source_id,
        "source_file": source_file,
        "status": "proposed",
        "proposed_by": "hand",
        "approved_by": None,
        "approved_at": None,
        "accepted_warnings": [],
        "columns": columns_for(header, mapped),
    }
    base.update(changes)
    return base


def flex_mapping(mapped, **changes):
    return mapping_dict(FLEX_HEADER, mapped, source_id="PSI-69", source_file=FLEX_FILE, **changes)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class FakeModel:
    """Stands in for app.llm.complete. It returns the queued answers in order."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, prompt, system="", timeout=30.0):
        self.calls.append({"prompt": prompt, "system": system})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def never_called(prompt, system="", timeout=30.0):
    raise AssertionError("the model must not be called here")


def propose_bass(data_dir, bass, model, **options):
    return m.propose.propose("PSI-25", bass, data_dir, complete=model, model_name="fake-model", now=now, **options)


def propose_flex(data_dir, flex, model, **options):
    return m.propose.propose("PSI-69", flex, data_dir, complete=model, model_name="fake-model", now=now, **options)


def mapping_file(data_dir, source_id="PSI-25"):
    return data_dir / "mappings" / f"{source_id}.json"


def proposal_copies(data_dir):
    folder = data_dir / "proposals"
    return sorted(folder.glob("*.json")) if folder.exists() else []


def run(*arguments):
    """Run the command line as a person would, without loading backend/.env."""
    return m.cli.main([str(argument) for argument in arguments])


# ---------- Check (tests 5, 6, 7, 32, 33) ----------


def test_05_missing_or_unknown_column_is_an_error(bass):
    table = m.tables.read_table(bass)

    short = schemas.MappingFile.model_validate(mapping_dict(BASS_HEADER[:-1], BASS_GOOD))
    result = m.check.check_mapping(short, table)
    assert any("Final CO (ppm)" in error and "missing" in error for error in result.errors)

    extra = schemas.MappingFile.model_validate(mapping_dict(BASS_HEADER + ["Flame length; cm"], BASS_GOOD))
    result = m.check.check_mapping(extra, table)
    assert any("Flame length; cm" in error for error in result.errors)

    complete = schemas.MappingFile.model_validate(mapping_dict(BASS_HEADER, BASS_GOOD))
    assert m.check.check_mapping(complete, table).errors == []


def test_06_two_columns_for_one_field_are_an_error(data_dir, bass):
    table = m.tables.read_table(bass)
    twice = dict(BASS_GOOD)
    twice["Calibrated final O2 % by vol"] = ("oxygen_pct", "percent")
    path = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER, twice))
    result = m.check.check_file(path, table)
    assert any("same field" in error for error in result.errors)


def test_07_values_out_of_range_give_a_warning(data_dir, flex):
    table = m.tables.read_table(flex)

    as_percent = dict(FLEX_GOOD)
    as_percent["O initial ambient composition; mole fraction"] = ("oxygen_pct", "percent")
    mapping = schemas.MappingFile.model_validate(flex_mapping(as_percent))
    warnings = m.check.check_mapping(mapping, table).warnings
    assert "percent_looks_like_fraction:O initial ambient composition; mole fraction" in warnings

    rows = [dict(FLEX_ROWS[0], **{"O %": "140", "Pressure kPa": "-3", "Flow cm/s": "-1"})]
    header = FLEX_HEADER + ["O %", "Pressure kPa", "Flow cm/s"]
    odd = write_table(data_dir, "PSI-70_Experimental table_ODD.csv", header, rows)
    mapped = {"O %": ("oxygen_pct", "percent"), "Pressure kPa": ("pressure_kpa", "kPa"), "Flow cm/s": ("flow_cm_s", "cm/s")}
    mapping = schemas.MappingFile.model_validate(
        mapping_dict(header, mapped, source_id="PSI-70", source_file=odd.name)
    )
    warnings = m.check.check_mapping(mapping, m.tables.read_table(odd)).warnings
    assert "oxygen_above_100:O %" in warnings
    assert "pressure_not_positive:Pressure kPa" in warnings
    assert "negative_value:Flow cm/s" in warnings


def test_32_a_column_listed_twice_is_an_error(data_dir, bass):
    table = m.tables.read_table(bass)
    payload = mapping_dict(BASS_HEADER, BASS_GOOD)
    payload["columns"].append(
        {"source_column": "Fan display", "target_field": "flow_cm_s", "unit": "cm/s", "confidence": "low", "note": None}
    )
    path = write_json(mapping_file(data_dir), payload)
    result = m.check.check_file(path, table)
    assert any("listed twice" in error and "Fan display" in error for error in result.errors)


def test_33_unit_not_visible_in_the_column_name_gives_a_warning(data_dir, bass, flex):
    fan = dict(BASS_GOOD)
    fan["Fan display"] = ("flow_cm_s", "cm/s")
    mapping = schemas.MappingFile.model_validate(mapping_dict(BASS_HEADER, fan))
    result = m.check.check_mapping(mapping, m.tables.read_table(bass))
    assert result.errors == []
    assert FAN_WARNING in result.warnings
    assert "unit_not_in_column_name:Calibrated initial O2 % by vol" not in result.warnings

    table = m.tables.read_table(flex)
    wrong = dict(FLEX_GOOD)
    wrong["Ambient pressure; mmHg"] = ("pressure_kpa", "kPa")
    mapping = schemas.MappingFile.model_validate(flex_mapping(wrong))
    assert "unit_not_in_column_name:Ambient pressure; mmHg" in m.check.check_mapping(mapping, table).warnings

    right = schemas.MappingFile.model_validate(flex_mapping(FLEX_GOOD))
    assert m.check.check_mapping(right, table).warnings == {}

    # A unit name inside a longer unit name does not count: m/s is not cm/s, a factor of 100.
    header = ["Test #", "Flow; cm/s", "Speed (mm/s)"]
    flow = m.tables.read_table(
        write_table(data_dir, "PSI-71_Experimental table_FLOW.csv", header, [{"Test #": "1", "Flow; cm/s": "20", "Speed (mm/s)": "5"}])
    )
    for column_name, declared, warned in (
        ("Flow; cm/s", "m/s", True),
        ("Flow; cm/s", "mm/s", True),
        ("Flow; cm/s", "cm/s", False),
        ("Speed (mm/s)", "m/s", True),
        ("Speed (mm/s)", "mm/s", False),
    ):
        mapping = schemas.MappingFile.model_validate(
            mapping_dict(header, {column_name: ("flow_cm_s", declared)}, source_id="PSI-71", source_file=flow.path.name)
        )
        warnings = m.check.check_mapping(mapping, flow).warnings
        assert (f"unit_not_in_column_name:{column_name}" in warnings) is warned, (column_name, declared)


# ---------- Propose (tests 8 to 14, 28, 29, 31, 35, 37, 41) ----------


def test_08_good_answer_becomes_a_proposed_file_with_an_untouched_copy(data_dir, bass):
    model = FakeModel(answer_for(BASS_HEADER, BASS_GOOD))
    result = propose_bass(data_dir, bass, model)

    assert len(model.calls) == 1
    written = schemas.MappingFile.model_validate(read_json(mapping_file(data_dir)))
    assert written.status == "proposed"
    assert written.proposed_by == "fake-model"
    assert [c.source_column for c in written.columns] == BASS_HEADER
    assert result.check.errors == []

    copies = proposal_copies(data_dir)
    assert len(copies) == 1
    assert read_json(copies[0]) == read_json(mapping_file(data_dir))


def test_09_the_model_sets_nothing_but_the_columns(data_dir, bass):
    hostile = {
        "investigation_id": "psi-99",
        "source_id": "PSI-99",
        "source_file": "another table.csv",
        "status": "approved",
        "proposed_by": "a person",
        "approved_by": "the model",
        "approved_at": "2026-01-01T00:00:00Z",
        "accepted_warnings": [FAN_WARNING],
        "dataset": "tests",
        "columns": [dict(column, value=22.2, approved=True) for column in columns_for(BASS_HEADER, BASS_GOOD)],
    }
    propose_bass(data_dir, bass, FakeModel(json.dumps(hostile)))

    for path in [mapping_file(data_dir)] + proposal_copies(data_dir):
        written = read_json(path)
        assert set(written) == {
            "source_id", "source_file", "status", "proposed_by", "approved_by", "approved_at",
            "accepted_warnings", "columns",
        }
        assert written["source_id"] == "PSI-25"
        assert written["source_file"] == BASS_FILE
        assert written["status"] == "proposed"
        assert written["proposed_by"] == "fake-model"
        assert written["approved_by"] is None
        assert written["approved_at"] is None
        assert written["accepted_warnings"] == []
        for column in written["columns"]:
            assert set(column) == {"source_column", "target_field", "unit", "confidence", "note"}


def test_10_json_is_found_inside_text_and_code_marks(data_dir, bass):
    wrapped = "Here is the mapping you asked for:\n```json\n" + answer_for(BASS_HEADER, BASS_GOOD) + "\n```\nLet me know."
    propose_bass(data_dir, bass, FakeModel(wrapped))
    written = schemas.MappingFile.model_validate(read_json(mapping_file(data_dir)))
    assert {c.source_column: c.target_field for c in written.columns}["Fuel Sample Material"] == "fuel"


def test_11_an_invalid_answer_gets_one_retry_then_nothing_is_written(data_dir, bass):
    retry_note = m.propose.RETRY_NOTE
    model = FakeModel("I cannot produce JSON today.", answer_for(BASS_HEADER, BASS_GOOD))
    propose_bass(data_dir, bass, model)
    assert len(model.calls) == 2
    assert retry_note not in model.calls[0]["prompt"]
    assert "JSON" in model.calls[1]["prompt"].split(retry_note)[1]  # the retry says what was wrong
    assert mapping_file(data_dir).exists()

    # A second table: the answer leaves a column out both times.
    other = data_dir.parent / "data2"
    table = write_table(other, BASS_FILE, BASS_HEADER, BASS_ROWS)
    short = answer_for(BASS_HEADER[:-1], BASS_GOOD)
    model = FakeModel(short, short)
    with pytest.raises(m.propose.ProposeFailed):
        m.propose.propose("PSI-25", table, other, complete=model, model_name="fake-model", now=now)
    assert len(model.calls) == 2
    told = model.calls[1]["prompt"].split(retry_note)[1]
    assert "Final CO (ppm)" in told and "missing" in told  # the checker's own words, not just the header
    assert not mapping_file(other).exists()
    assert proposal_copies(other) == []


def test_12_without_a_working_model_nothing_is_written(data_dir, bass, capsys):
    model = FakeModel(llm.LLMUnavailable("LLM_API_KEY is not set."))
    with pytest.raises(m.propose.ProposeFailed) as failure:
        propose_bass(data_dir, bass, model)
    assert "model" in str(failure.value).lower()
    assert not mapping_file(data_dir).exists()
    assert proposal_copies(data_dir) == []

    # The command line gives the same clear message and a failing exit code.
    assert run("propose", "PSI-25", "--data-dir", data_dir) == 1
    assert "LLM_API_KEY" in capsys.readouterr().err
    assert not mapping_file(data_dir).exists()
    # The command function reads no .env file; only the real entry point does.
    assert os.getenv("SUPABASE_KEY") is None and os.getenv("LLM_API_KEY") is None


def test_13_the_prompt_holds_the_table_and_the_contract_and_no_setting(data_dir, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-SECRET-MODEL-KEY")
    monkeypatch.setenv("SUPABASE_KEY", "sb_secret_TEST-SUPABASE-KEY")
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    rows = [dict(BASS_ROWS[0], **{"Sample #": f"ROW-{number:02d}"}) for number in range(1, 13)]
    table = m.tables.read_table(write_table(data_dir, BASS_FILE, BASS_HEADER, rows))

    system, prompt = m.propose.build_prompt(table)
    text = system + "\n" + prompt

    for name in BASS_HEADER:
        assert name in prompt
    assert "ROW-08" in prompt
    assert "ROW-09" not in prompt
    for field in schemas.MAPPING_TARGET_FIELDS:
        assert field in text
    for units in schemas.MAPPING_UNITS.values():
        for unit in units:
            assert unit in text
    for secret in ("SECRET-MODEL-KEY", "TEST-SUPABASE-KEY", "example-project", str(data_dir)):
        assert secret not in text


def test_14_an_existing_mapping_file_is_not_overwritten(data_dir, bass, capsys):
    for status in ("proposed", "approved"):
        changes = {}
        if status == "approved":
            changes = {"status": "approved", "approved_by": "A. Person", "approved_at": "2026-11-14T12:00:00Z"}
        path = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER, BASS_GOOD, **changes))
        before = path.read_bytes()

        with pytest.raises(m.propose.MappingExists):
            propose_bass(data_dir, bass, never_called)
        assert path.read_bytes() == before

        # The same through the command a person runs.
        assert run("propose", "PSI-25", "--data-dir", data_dir) == 1
        assert "--force" in capsys.readouterr().err
        assert path.read_bytes() == before
        assert proposal_copies(data_dir) == []


def test_28_file_with_byte_order_mark_space_and_micro_sign_is_read(data_dir):
    header = ["Test #", "Particle size; µm", "Calibrated initial O2 % by vol"]
    rows = [{"Test #": "S1", "Particle size; µm": "0.2", "Calibrated initial O2 % by vol": "21.5"}]
    path = write_table(data_dir, "PSI-102_Experimental table_SAME sample.csv", header, rows, encoding="utf-8-sig")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")

    table = m.tables.read_table(path)
    assert table.header == header  # no byte-order mark in the first name, and µ is intact
    assert table.rows[0]["Particle size; µm"] == "0.2"

    mapped = {"Test #": ("test_label", None), "Calibrated initial O2 % by vol": ("oxygen_pct", "percent")}
    m.propose.propose(
        "PSI-102", path, data_dir, complete=FakeModel(answer_for(header, mapped)), model_name="fake-model", now=now
    )
    written = json.loads(mapping_file(data_dir, "PSI-102").read_bytes().decode("utf-8"))
    assert written["columns"][1]["source_column"] == "Particle size; µm"
    assert written["source_file"] == "PSI-102_Experimental table_SAME sample.csv"


def test_29_force_replaces_an_existing_file_and_resets_the_status(data_dir, bass):
    approved = mapping_dict(
        BASS_HEADER, {}, status="approved", approved_by="A. Person", approved_at="2026-11-14T12:00:00Z"
    )
    write_json(mapping_file(data_dir), approved)
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, BASS_GOOD)), force=True)
    written = schemas.MappingFile.model_validate(read_json(mapping_file(data_dir)))
    assert written.status == "proposed"
    assert written.approved_by is None
    assert {c.source_column: c.target_field for c in written.columns}["Test #"] == "test_label"


def test_31_a_repeated_column_name_in_the_table_is_refused(data_dir, capsys):
    raw = data_dir / "raw"
    raw.mkdir(parents=True)
    path = raw / "PSI-77_Experimental table_TWICE.csv"
    path.write_text("Test #,Oxygen %,Oxygen %\nA1,21,22\n", encoding="utf-8")

    with pytest.raises(m.tables.TableError) as failure:
        m.tables.read_table(path)
    assert "Oxygen %" in str(failure.value)

    assert run("propose", "PSI-77", "--data-dir", data_dir) == 1
    assert "Oxygen %" in capsys.readouterr().err
    assert not mapping_file(data_dir, "PSI-77").exists()


def test_35_a_failed_forced_run_leaves_the_old_file_byte_for_byte(data_dir, bass, monkeypatch, capsys):
    path = write_json(
        mapping_file(data_dir),
        mapping_dict(BASS_HEADER, BASS_GOOD, status="approved", approved_by="A. Person", approved_at="2026-11-14T12:00:00Z"),
    )
    before = path.read_bytes()

    with pytest.raises(m.propose.ProposeFailed):
        propose_bass(data_dir, bass, FakeModel(llm.LLMUnavailable("timeout")), force=True)
    assert path.read_bytes() == before

    with pytest.raises(m.propose.ProposeFailed):
        propose_bass(data_dir, bass, FakeModel("not json", "still not json"), force=True)
    assert path.read_bytes() == before

    # Through the command line, forced, with no working model.
    assert run("propose", "PSI-25", "--force", "--data-dir", data_dir) == 1
    capsys.readouterr()
    assert path.read_bytes() == before

    def failing_replace(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(m.store.os, "replace", failing_replace)
    with pytest.raises(OSError):
        propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, {})), force=True)
    assert path.read_bytes() == before
    assert [p.name for p in (data_dir / "mappings").iterdir()] == ["PSI-25.json"]  # no half-written file left
    assert proposal_copies(data_dir) == []


def test_37_untouched_copies_live_outside_the_folder_that_t2_reads(data_dir, bass):
    hostile = json.dumps({"status": "approved", "approved_by": "the model", "columns": columns_for(BASS_HEADER, BASS_GOOD)})
    result = propose_bass(data_dir, bass, FakeModel(hostile))

    assert result.copy_path.parent == data_dir / "proposals"
    assert read_json(result.copy_path)["status"] == "proposed"
    in_mappings = sorted(p.name for p in (data_dir / "mappings").iterdir())
    assert in_mappings == ["PSI-25.json"]
    for path in (data_dir / "mappings").glob("*.json"):
        schemas.MappingFile.model_validate(read_json(path))

    # A second proposal at the same moment keeps the first copy.
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, {})), force=True)
    copies = proposal_copies(data_dir)
    assert len(copies) == 2
    latest = m.store.latest_proposal(data_dir, "PSI-25")
    assert latest == copies[-1]
    assert all(column["target_field"] is None for column in read_json(latest)["columns"])


def test_41_the_prompt_holds_no_column_name_of_another_table(bass, flex):
    bass_system, bass_prompt = m.propose.build_prompt(m.tables.read_table(bass))
    flex_system, flex_prompt = m.propose.build_prompt(m.tables.read_table(flex))
    assert bass_system == flex_system  # the instructions do not depend on the table

    def foreign(names, own):
        """Names of the other table that are not part of one of this table's own names."""
        return [name for name in names if not any(name in own_name for own_name in own)]

    foreign_in_bass = foreign(FLEX_HEADER, BASS_HEADER)
    foreign_in_flex = foreign(BASS_HEADER, FLEX_HEADER)
    assert "Ambient pressure; mmHg" in foreign_in_bass and "Fan display" in foreign_in_flex
    for name in foreign_in_bass:
        assert name not in bass_prompt
    for name in foreign_in_flex:
        assert name not in flex_prompt
    for name in BASS_HEADER + FLEX_HEADER:
        if len(name) > 4:  # short names such as "PI" or "Fuel" are ordinary words
            assert name not in bass_system


# ---------- Review and approve (tests 15, 16, 17, 21, 34) ----------


def test_15_a_file_that_cannot_pass_the_check_is_not_approved(data_dir, bass):
    path = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER[:-1], BASS_GOOD))
    before = path.read_bytes()
    with pytest.raises(m.approve.ApprovalRefused) as failure:
        m.approve.approve("PSI-25", data_dir, by="A. Person", now=now)
    assert "Final CO (ppm)" in str(failure.value)
    assert path.read_bytes() == before

    # A file that names another table is refused, even with a correct list of columns.
    stray = write_json(mapping_file(data_dir, "PSI-69"), mapping_dict(BASS_HEADER, BASS_GOOD))
    write_table(data_dir, FLEX_FILE, BASS_HEADER, BASS_ROWS)
    with pytest.raises(m.approve.ApprovalRefused) as failure:
        m.approve.approve("PSI-69", data_dir, by="A. Person", now=now)
    assert "PSI-25" in str(failure.value)
    assert read_json(stray)["status"] == "proposed"

    # No table, no check, no approval.
    good = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER, BASS_GOOD))
    bass.unlink()
    with pytest.raises(m.approve.ApprovalRefused) as failure:
        m.approve.approve("PSI-25", data_dir, by="A. Person", now=now)
    assert "table" in str(failure.value).lower()
    assert read_json(good)["status"] == "proposed"


def test_16_approval_needs_a_name(data_dir, bass):
    path = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER, BASS_GOOD))
    before = path.read_bytes()
    for name in ("", "   "):
        with pytest.raises(m.approve.ApprovalRefused):
            m.approve.approve("PSI-25", data_dir, by=name, now=now)
    assert path.read_bytes() == before


def test_17_approval_sets_status_name_and_date_and_nothing_else(data_dir, bass):
    original = mapping_dict(BASS_HEADER, BASS_GOOD, proposed_by="fake-model")
    path = write_json(mapping_file(data_dir), original)
    m.approve.approve("PSI-25", data_dir, by="A. Person", now=now)

    approved = read_json(path)
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "A. Person"
    assert approved["approved_at"] == "2026-11-14T15:00:00Z"
    assert set(approved) == set(original)
    changed = {key for key in approved if approved[key] != original[key]}
    assert changed == {"status", "approved_by", "approved_at"}
    schemas.MappingFile.model_validate(approved)


def test_21_review_shows_each_column_with_samples_and_check_results(data_dir, bass):
    fan = dict(BASS_GOOD)
    fan["Fan display"] = ("flow_cm_s", "cm/s")
    mapping = schemas.MappingFile.model_validate(mapping_dict(BASS_HEADER, fan))
    table = m.tables.read_table(bass)
    text = m.review.render_review(mapping, table, m.check.check_mapping(mapping, table))

    lines = text.splitlines()
    for name in BASS_HEADER:
        assert sum(1 for line in lines if line.lstrip().startswith(name + " ")) == 1
    fan_line = next(line for line in lines if line.lstrip().startswith("Fan display "))
    assert "flow_cm_s" in fan_line and "cm/s" in fan_line
    assert "62" in fan_line and "47" in fan_line  # sample values from the table
    assert FAN_WARNING in text


def test_34_no_approval_while_a_warning_stands(data_dir, bass, capsys):
    fan = dict(BASS_GOOD)
    fan["Fan display"] = ("flow_cm_s", "cm/s")
    path = write_json(mapping_file(data_dir), mapping_dict(BASS_HEADER, fan))
    before = path.read_bytes()

    with pytest.raises(m.approve.ApprovalRefused) as failure:
        m.approve.approve("PSI-25", data_dir, by="A. Person", now=now)
    assert FAN_WARNING in str(failure.value)
    assert path.read_bytes() == before

    with pytest.raises(m.approve.ApprovalRefused):  # a warning that does not stand cannot be accepted
        m.approve.approve("PSI-25", data_dir, by="A. Person", accept=[FAN_WARNING, "oxygen_above_100:Fan display"], now=now)
    assert path.read_bytes() == before

    # The command line refuses too, then approves once the person accepts the warning by name.
    assert run("approve", "PSI-25", "--by", "A. Person", "--data-dir", data_dir) == 1
    assert FAN_WARNING in capsys.readouterr().err
    assert path.read_bytes() == before
    assert run("approve", "PSI-25", "--by", "A. Person", "--accept", FAN_WARNING, "--data-dir", data_dir) == 0
    capsys.readouterr()
    approved = read_json(path)
    assert approved["status"] == "approved"
    assert approved["accepted_warnings"] == [FAN_WARNING]


def test_34b_every_standing_warning_must_be_accepted(data_dir, flex):
    two = dict(FLEX_GOOD)
    two["Ambient pressure; mmHg"] = ("pressure_kpa", "kPa")
    two["Burn time; s"] = ("flow_cm_s", "cm/s")
    path = write_json(mapping_file(data_dir, "PSI-69"), flex_mapping(two))
    before = path.read_bytes()
    pressure = "unit_not_in_column_name:Ambient pressure; mmHg"
    burn = "unit_not_in_column_name:Burn time; s"

    with pytest.raises(m.approve.ApprovalRefused) as failure:
        m.approve.approve("PSI-69", data_dir, by="A. Person", accept=[pressure], now=now)
    assert burn in str(failure.value)
    assert path.read_bytes() == before

    m.approve.approve("PSI-69", data_dir, by="A. Person", accept=[burn, pressure], now=now)
    assert read_json(path)["accepted_warnings"] == sorted([burn, pressure])


# ---------- Score (tests 18, 19, 20, 30, 39, 40) ----------


def gold_file(data_dir, source_id="PSI-25"):
    return data_dir / "gold" / "mappings" / f"{source_id}.json"


def write_gold(data_dir, header, mapped, source_id="PSI-25", source_file=BASS_FILE):
    payload = mapping_dict(
        header, mapped, source_id=source_id, source_file=source_file,
        status="approved", approved_by="A. Person", approved_at="2026-11-14T12:00:00Z",
    )
    return write_json(gold_file(data_dir, source_id), payload)


def test_18_a_proposal_equal_to_the_gold_scores_full(data_dir, bass, capsys):
    write_gold(data_dir, BASS_HEADER, BASS_GOOD)
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, BASS_GOOD)))

    report = m.score.score(data_dir)
    (table,) = report.tables
    assert (table.mapped_found, table.mapped_total) == (3, 3)
    assert (table.all_correct, table.all_total) == (17, 17)
    assert table.false_mappings == []
    assert "3 of 3" in report.render()

    assert run("score", "--data-dir", data_dir) == 0
    printed = capsys.readouterr().out
    assert "3 of 3" in printed and "17 of 17" in printed


def test_19_each_kind_of_error_is_counted_in_its_own_group(data_dir, flex):
    write_gold(data_dir, FLEX_HEADER, FLEX_GOOD, source_id="PSI-69", source_file=FLEX_FILE)
    proposed = {
        "FLEX Identifier": ("test_label", None),  # correct
        "Fuel": ("geometry", None),  # wrong field
        "Ambient pressure; mmHg": ("pressure_kpa", "kPa"),  # wrong unit
        # "O initial ambient composition; mole fraction" is missed
        "Test end": ("outcome", None),  # correct
        "Burn time; s": ("flow_cm_s", "cm/s"),  # false mapping
    }
    propose_flex(data_dir, flex, FakeModel(answer_for(FLEX_HEADER, proposed)))

    (table,) = m.score.score(data_dir).tables
    assert (table.wrong_field, table.wrong_unit, table.missed) == (1, 1, 1)
    assert table.false_mappings == ["Burn time; s"]
    assert (table.mapped_found, table.mapped_total) == (2, 5)
    assert (table.all_correct, table.all_total) == (11, 15)


def test_20_a_table_without_a_gold_mapping_is_skipped_and_named(data_dir, bass, flex):
    write_gold(data_dir, BASS_HEADER, BASS_GOOD)
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, BASS_GOOD)))
    propose_flex(data_dir, flex, FakeModel(answer_for(FLEX_HEADER, FLEX_GOOD)))

    report = m.score.score(data_dir)
    assert [table.source_id for table in report.tables] == ["PSI-25"]
    assert any("PSI-69" in line for line in report.skipped)
    assert "PSI-69" in report.render()


def test_30_different_column_lists_give_an_error_not_a_score(data_dir, bass, capsys):
    write_gold(data_dir, BASS_HEADER + ["Flame length; cm"], BASS_GOOD)
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, BASS_GOOD)))

    report = m.score.score(data_dir)
    assert report.tables == []
    assert any("PSI-25" in error and "Flame length; cm" in error for error in report.errors)
    assert run("score", "--data-dir", data_dir) == 1
    assert "Flame length; cm" in capsys.readouterr().out


def test_39_a_corrected_and_approved_mapping_still_counts_as_wrong(data_dir, flex):
    write_gold(data_dir, FLEX_HEADER, FLEX_GOOD, source_id="PSI-69", source_file=FLEX_FILE)
    wrong = dict(FLEX_GOOD)
    wrong["Ambient pressure; mmHg"] = ("pressure_kpa", "kPa")
    propose_flex(data_dir, flex, FakeModel(answer_for(FLEX_HEADER, wrong)))

    # A person corrects the mapping file and approves it.
    write_json(mapping_file(data_dir, "PSI-69"), flex_mapping(FLEX_GOOD))
    m.approve.approve("PSI-69", data_dir, by="A. Person", now=now)

    (table,) = m.score.score(data_dir).tables
    assert table.wrong_unit == 1
    assert (table.mapped_found, table.mapped_total) == (4, 5)


def test_40_a_proposal_that_maps_nothing_scores_zero_on_the_mapped_columns(data_dir, bass):
    write_gold(data_dir, BASS_HEADER, BASS_GOOD)
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, {})))

    report = m.score.score(data_dir)
    (table,) = report.tables
    assert (table.mapped_found, table.mapped_total) == (0, 3)
    assert (table.all_correct, table.all_total) == (14, 17)
    assert table.missed == 3
    text = report.render()
    assert "0 of 3" in text
    assert text.index("0 of 3") < text.index("14 of 17")  # the main number comes first


# ---------- Whole flow (tests 22, 23, 24) ----------


def test_22_whole_flow_with_a_fake_model(data_dir, bass, capsys):
    propose_bass(data_dir, bass, FakeModel(answer_for(BASS_HEADER, BASS_GOOD)))

    assert run("review", "PSI-25", "--data-dir", data_dir) == 0
    assert "Fuel Sample Material" in capsys.readouterr().out
    assert run("approve", "PSI-25", "--by", "A. Person", "--data-dir", data_dir) == 0

    final = schemas.MappingFile.model_validate(read_json(mapping_file(data_dir)))
    assert final.status == "approved"
    assert final.approved_by == "A. Person"
    table = m.tables.read_table(bass)
    assert m.check.check_mapping(final, table).errors == []


def test_23_a_mapping_written_by_hand_needs_no_model(data_dir, flex, capsys):
    write_json(mapping_file(data_dir, "PSI-69"), flex_mapping(FLEX_GOOD))
    assert run("review", "PSI-69", "--data-dir", data_dir) == 0
    assert run("approve", "PSI-69", "--by", "A. Person", "--data-dir", data_dir) == 0
    capsys.readouterr()

    final = schemas.MappingFile.model_validate(read_json(mapping_file(data_dir, "PSI-69")))
    assert (final.status, final.proposed_by) == ("approved", "hand")


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="needs LLM_API_KEY: this test calls the real model")
def test_24_the_real_model_gives_a_file_that_passes_the_check(data_dir):
    """A smoke test. It does not prove that the mapping is right; the score does that."""
    tables = sorted((REPO_DATA / "raw").glob("PSI-*_*.csv"))
    if not tables:
        pytest.skip("no PSI table in data/raw yet")
    source_id = tables[0].name.split("_")[0]
    result = m.propose.propose(source_id, tables[0], data_dir, now=now)
    assert result.check.errors == []
    assert read_json(mapping_file(data_dir, source_id))["status"] == "proposed"


# ---------- Existing code (tests 26, 42) ----------


def test_26_llm_complete_keeps_its_inputs():
    parameters = inspect.signature(llm.complete).parameters
    assert list(parameters) == ["prompt", "system", "timeout"]
    assert parameters["system"].default == ""
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("hello")


def test_42_llm_complete_sends_the_agreed_request(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/")
    seen = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "the answer"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, json=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    assert llm.complete("the question", system="the rules", timeout=5.0) == "the answer"
    assert seen["url"] == "https://llm.example.test/chat/completions"
    assert seen["headers"] == {"Authorization": "Bearer sk-test-key"}
    assert seen["json"] == {
        "model": "test-model",
        "messages": [{"role": "system", "content": "the rules"}, {"role": "user", "content": "the question"}],
    }
    assert seen["timeout"] == 5.0


# ---------- Guard (test 38) ----------


def test_38_tests_touch_no_real_file_and_no_network(repo_is_untouched, data_dir):
    with pytest.raises(AssertionError):
        httpx.post("https://example.test")
    with pytest.raises(OSError):
        socket.create_connection(("192.0.2.1", 80), timeout=1)  # a test address; the guard answers first
    assert REPO_DATA not in data_dir.parents and BACKEND not in data_dir.parents
    assert repo_state() == repo_is_untouched
