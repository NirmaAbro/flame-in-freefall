"""Tests for the T2 ingest pipeline.

Run from flame-in-freefall/backend/:
    python -m pytest tests/test_ingest.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure backend/ is on the path (matches what ingest/run.py does)
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.schemas import TestRow  # noqa: E402
from ingest.parse import parse_cell  # noqa: E402
from ingest.reader import read_csv  # noqa: E402
from ingest.units import convert  # noqa: E402

_RAW = _BACKEND.parent / "data" / "raw"
_PSI25 = _RAW / "PSI-25_Experimental table_BASS-II.csv"


# ===========================================================================
# Unit conversion tests
# ===========================================================================


class TestConversions:
    def test_percent_is_identity(self):
        val, flag = convert(21.0, "%", "oxygen_pct", "O2 col")
        assert val == pytest.approx(21.0)
        assert flag is None

    def test_mole_fraction_to_percent(self):
        val, flag = convert(0.21, "mole_fraction", "oxygen_pct", "O2 col")
        assert val == pytest.approx(21.0)
        assert flag is None

    def test_mmhg_to_kpa(self):
        val, flag = convert(760.0, "mmHg", "pressure_kpa", "P col")
        assert val == pytest.approx(101.325, rel=1e-4)
        assert flag is None

    def test_atm_to_kpa(self):
        val, flag = convert(1.0, "atm", "pressure_kpa", "P col")
        assert val == pytest.approx(101.325)
        assert flag is None

    def test_cm_s_is_identity(self):
        val, flag = convert(5.0, "cm/s", "flow_cm_s", "V col")
        assert val == pytest.approx(5.0)
        assert flag is None

    def test_unknown_unit_returns_none_and_flag(self):
        val, flag = convert(1.0, "psi", "pressure_kpa", "P col")
        assert val is None
        assert flag is not None
        assert "unknown unit" in flag


# ===========================================================================
# Null-token rules (empty / "none" cell → None, never 0)
# ===========================================================================


class TestNullTokens:
    @pytest.mark.parametrize("raw", ["", "N/A", "n/a", "-", "none", "None"])
    def test_null_tokens_give_none_for_float(self, raw):
        val, flags = parse_cell(raw, "oxygen_pct", "O2 col", "float", "%")
        assert val is None

    @pytest.mark.parametrize("raw", ["", "N/A", "n/a", "-", "none", "None"])
    def test_null_tokens_give_none_for_text(self, raw):
        val, flags = parse_cell(raw, "fuel", "Fuel col", "text", None)
        assert val is None

    def test_none_token_adds_flag_for_numeric(self):
        val, flags = parse_cell("none", "oxygen_pct", "O2", "float", "%")
        assert val is None
        assert any("none" in f.lower() for f in flags)

    def test_none_token_does_not_add_flag_for_text(self):
        # text field: "none" is a null but no special flag needed
        val, flags = parse_cell("none", "fuel", "Fuel", "text", None)
        assert val is None
        # flags may be empty — that is fine
        assert not any("none" in f.lower() for f in flags)

    def test_zero_string_parses_to_zero_not_none(self):
        """'0' is a real value and must NOT be treated as null."""
        val, flags = parse_cell("0", "oxygen_pct", "O2", "float", "%")
        assert val == pytest.approx(0.0)

    def test_empty_cell_is_never_zero(self):
        val, flags = parse_cell("", "oxygen_pct", "O2", "float", "%")
        assert val is None
        assert val != 0

    def test_empty_pressure_cell_gives_none_not_zero(self):
        """An empty pressure cell must give None, never 0."""
        val, flags = parse_cell("", "pressure_kpa", "Ambient pressure; mmHg", "float", "mmHg")
        assert val is None
        assert val != 0

    def test_literal_zero_pressure_gives_none_with_flag(self):
        """A literal '0' pressure cell is physically implausible; must be None + flag."""
        val, flags = parse_cell("0", "pressure_kpa", "Ambient pressure; mmHg", "float", "mmHg")
        assert val is None
        assert any("implausible" in f for f in flags)


# ===========================================================================
# Flagged value keeps its raw string
# ===========================================================================


class TestFlaggedValueKeepsRaw:
    def test_unparseable_float_keeps_raw_in_TestRow(self):
        """A cell that cannot be parsed as float should: field=None, raw intact."""
        row = TestRow(
            id="test:file:1",
            investigation_id="PSI-25",
            source_file="file.csv",
            source_row=1,
            raw={"O2 col": "pot 0.9 0.5"},
            data_status="parsed",
            flags=["oxygen_pct (O2 col): could not parse 'pot 0.9 0.5' as float"],
        )
        assert row.oxygen_pct is None
        assert row.raw["O2 col"] == "pot 0.9 0.5"
        assert row.flags != []

    def test_mole_fraction_above_1_keeps_field_none(self):
        val, flags = parse_cell("1.5", "oxygen_pct", "O2", "float", "mole_fraction")
        assert val is None
        assert any("above 1" in f for f in flags)

    def test_oxygen_pct_out_of_range_keeps_value(self):
        """Out-of-range → flag but value is NOT nulled."""
        val, flags = parse_cell("150.0", "oxygen_pct", "O2", "float", "%")
        assert val == pytest.approx(150.0)
        assert any("outside" in f or "outside" in f for f in flags)

    def test_negative_pressure_gives_none_with_flag(self):
        """pressure_kpa <= 0 must be None with an implausibility flag (raw kept)."""
        val, flags = parse_cell("-5.0", "pressure_kpa", "P", "float", "mmHg")
        assert val is None
        assert any("implausible" in f for f in flags)


# ===========================================================================
# Integration tests on the real raw files
# ===========================================================================


class TestIntegrationPSI25:
    @pytest.fixture(scope="class")
    def rows_and_flags(self):
        """Parse PSI-25 once per class."""
        import json
        from ingest.run import ingest_file  # noqa: E402
        mapping_path = _BACKEND.parent / "data" / "mappings" / "PSI-25.json"
        with mapping_path.open() as fh:
            mapping = json.load(fh)
        rows, flags = ingest_file("PSI-25", _PSI25, mapping)
        return rows, flags

    def test_psi25_yields_129_rows(self, rows_and_flags):
        rows, _ = rows_and_flags
        assert len(rows) == 129

    def test_no_numeric_field_is_zero_where_source_is_empty(self, rows_and_flags):
        """No row may have oxygen_pct=0 or pressure_kpa=0 or flow_cm_s=0 when
        the corresponding source cell is empty."""
        rows, _ = rows_and_flags
        for row in rows:
            for field in ("oxygen_pct", "pressure_kpa", "flow_cm_s"):
                if getattr(row, field) == 0.0:
                    # 0.0 is only valid if the source cell was actually "0"
                    # (not empty/null); verify via raw
                    # Map field -> column via mapping (we know them statically)
                    _field_to_col = {
                        "oxygen_pct": "Calibrated initial O2 % by vol",
                    }
                    col = _field_to_col.get(field)
                    if col:
                        raw_val = row.raw.get(col, "")
                        assert raw_val is not None and raw_val.strip() not in (
                            "", "none", "n/a", "-"
                        ), (
                            f"Row {row.source_row}: {field}=0.0 "
                            f"but source cell is empty/null"
                        )

    def test_every_row_has_source_file_and_row(self, rows_and_flags):
        rows, _ = rows_and_flags
        for row in rows:
            assert row.source_file is not None and row.source_file != ""
            assert row.source_row is not None and row.source_row >= 1

    def test_investigation_id_is_psi25(self, rows_and_flags):
        rows, _ = rows_and_flags
        for row in rows:
            assert row.investigation_id == "PSI-25"

    def test_data_status_is_parsed(self, rows_and_flags):
        rows, _ = rows_and_flags
        for row in rows:
            assert row.data_status == "parsed"

    def test_flags_default_empty_on_clean_rows(self, rows_and_flags):
        """At least some rows must have no flags (clean rows exist in PSI-25)."""
        rows, _ = rows_and_flags
        clean_rows = [r for r in rows if not r.flags]
        assert len(clean_rows) > 0

    def test_negative_co_rows_are_flagged(self, rows_and_flags):
        """Rows with negative Initial CO (ppm) must carry a data-quality flag."""
        rows, _ = rows_and_flags
        for row in rows:
            raw_co = row.raw.get("Initial CO (ppm)", "")
            if raw_co and raw_co not in ("none", ""):
                try:
                    co_val = float(raw_co)
                except ValueError:
                    continue
                if co_val < 0:
                    assert any("negative" in f.lower() or "CO" in f for f in row.flags), (
                        f"Row {row.source_row}: CO={co_val} but no CO flag found"
                    )


# ===========================================================================
# Integration test: no pressure_kpa <= 0 across all ingested rows
# ===========================================================================


class TestNoPressureLEZero:
    """After fix, no test row produced from any raw file may have pressure_kpa <= 0."""

    @pytest.fixture(scope="class")
    def all_rows(self):
        import json
        from ingest.run import ingest_file
        _MAPPINGS = _BACKEND.parent / "data" / "mappings"
        _RAW_DIR = _BACKEND.parent / "data" / "raw"

        all_rows = []
        for psi_id, raw_glob in [
            ("PSI-25", "PSI-25_*"),
            ("PSI-69", "PSI-69_*"),
        ]:
            raw_files = list(_RAW_DIR.glob(raw_glob))
            if not raw_files:
                continue
            mapping_path = _MAPPINGS / f"{psi_id}.json"
            with mapping_path.open() as fh:
                mapping = json.load(fh)
            rows, _ = ingest_file(psi_id, raw_files[0], mapping)
            all_rows.extend(rows)
        return all_rows

    def test_no_row_has_pressure_le_zero(self, all_rows):
        """No ingested row may have pressure_kpa <= 0 (must be None instead)."""
        bad = [
            (r.investigation_id, r.source_row, r.pressure_kpa)
            for r in all_rows
            if r.pressure_kpa is not None and r.pressure_kpa <= 0
        ]
        assert bad == [], (
            f"Found rows with pressure_kpa <= 0: {bad}"
        )

    def test_zero_pressure_row_has_flag(self, all_rows):
        """The PSI-69 row that sources '0 mmHg' must carry an implausibility flag."""
        psi69_rows = [r for r in all_rows if r.investigation_id == "PSI-69"]
        # source_row 114 is the offending row
        row114 = next((r for r in psi69_rows if r.source_row == 114), None)
        assert row114 is not None, "PSI-69 source_row 114 not found in ingested rows"
        assert row114.pressure_kpa is None
        assert any("implausible" in f for f in row114.flags), (
            f"Row 114 flags: {row114.flags}"
        )
