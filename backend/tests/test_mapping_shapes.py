"""T6 contract checks: the shape of a mapping file.

These are tests 1 to 4, 36 and 43 of the T6 plan. T2 reads mapping files through
this shape only, so the shape itself must refuse a bad file.

Run from the backend folder:  python -m pytest
"""
import pytest
from pydantic import ValidationError

from app import schemas


def column(**changes):
    base = {
        "source_column": "Calibrated initial O2 % by vol",
        "target_field": "oxygen_pct",
        "unit": "percent",
        "confidence": "high",
        "note": None,
    }
    base.update(changes)
    return base


def mapping(**changes):
    base = {
        "source_id": "PSI-25",
        "source_file": "PSI-25_Experimental table_BASS-II.csv",
        "status": "proposed",
        "proposed_by": "fake-model",
        "approved_by": None,
        "approved_at": None,
        "accepted_warnings": [],
        "columns": [column(), column(source_column="Fan display", target_field=None, unit=None)],
    }
    base.update(changes)
    return base


def rejected(payload):
    with pytest.raises(ValidationError):
        schemas.MappingFile.model_validate(payload)


def test_01_valid_mapping_file_is_accepted():
    parsed = schemas.MappingFile.model_validate(mapping())
    assert parsed.status == "proposed"
    assert [c.target_field for c in parsed.columns] == ["oxygen_pct", None]
    assert parsed.accepted_warnings == []


def test_02_unknown_target_field_is_an_error():
    rejected(mapping(columns=[column(target_field="temperature_c", unit=None)]))


def test_03_unit_that_does_not_belong_to_the_field_is_an_error():
    rejected(mapping(columns=[column(unit="mmHg")]))  # a pressure unit on oxygen
    rejected(mapping(columns=[column(unit="furlongs")]))  # not a unit of the contract
    rejected(mapping(columns=[column(target_field="pressure_kpa", unit="percent")]))


def test_04_number_field_needs_a_unit_and_text_field_takes_none():
    rejected(mapping(columns=[column(unit=None)]))  # oxygen without a unit
    rejected(mapping(columns=[column(source_column="Fuel", target_field="fuel", unit="percent")]))
    rejected(mapping(columns=[column(target_field=None, unit="percent")]))  # unused column with a unit
    schemas.MappingFile.model_validate(
        mapping(columns=[column(source_column="Fuel", target_field="fuel", unit=None)])
    )


def test_36_shape_alone_guards_what_t2_reads():
    approved = {"status": "approved", "approved_by": "A. Person", "approved_at": "2026-11-14T15:00:00Z"}
    schemas.MappingFile.model_validate(mapping(**approved))

    # Approval needs a real name and a real date.
    rejected(mapping(status="approved"))
    rejected(mapping(status="approved", approved_by="A. Person"))
    rejected(mapping(status="approved", approved_at="2026-11-14T15:00:00Z"))
    rejected(mapping(status="approved", approved_by="", approved_at="2026-11-14T15:00:00Z"))
    rejected(mapping(status="approved", approved_by="   ", approved_at="2026-11-14T15:00:00Z"))
    rejected(mapping(status="approved", approved_by="A. Person", approved_at="yesterday"))

    # A proposal cannot carry an approver, and no other status exists.
    rejected(mapping(approved_by="A. Person"))
    rejected(mapping(approved_at="2026-11-14T15:00:00Z"))
    rejected(mapping(status="verified"))

    # No key outside the contract, at either level.
    rejected({**mapping(), "dataset": "tests"})
    rejected({**mapping(), "investigation_id": "psi-25"})  # T2 finds the record through source_id
    rejected(mapping(columns=[{**column(), "value": 22.2}]))

    # A table column appears once, and a field has one source.
    rejected(mapping(columns=[column(), column(target_field=None, unit=None)]))
    rejected(mapping(columns=[column(), column(source_column="Calibrated final O2 % by vol")]))


def test_43_every_allowed_target_field_exists_on_testrow():
    test_row_fields = set(schemas.TestRow.model_fields)
    assert set(schemas.MAPPING_TARGET_FIELDS) <= test_row_fields
    assert set(schemas.MAPPING_UNITS) <= set(schemas.MAPPING_TARGET_FIELDS)
    assert set(schemas.MAPPING_TEXT_FIELDS).isdisjoint(schemas.MAPPING_UNITS)
    # Fields that a table cannot feed stay out of the mapping.
    for tool_owned in ("id", "investigation_id", "source_file", "source_row", "raw", "flags", "data_status"):
        assert tool_owned not in schemas.MAPPING_TARGET_FIELDS
