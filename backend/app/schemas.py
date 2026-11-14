"""Data shapes of the API (the contract).

The first part mirrors frontend/ignis-frontend/src/lib/types.ts field by field.
If a shape changes, change types.ts and this file together.

Rule from the frontend: a missing value is None (JSON null), never "" or 0.
"""
from datetime import datetime
from typing import Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

FuelClass = Literal["Solid", "Gas", "Liquid droplet", "Particulate / aerosol"]
DataStatus = Literal["sample", "parsed", "verified"]

T = TypeVar("T")


# ---------- Shapes the frontend already uses (types.ts) ----------


class SourceCitation(BaseModel):
    source_name: str
    source_url: str
    doi: Optional[str] = None
    location: Optional[str] = None
    accessed_at: str


class ConditionParameter(BaseModel):
    name: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    context: Optional[str] = None
    citation: SourceCitation


class FileRef(BaseModel):
    id: str
    title: str
    file_type: str
    description: Optional[str] = None
    source_url: str
    reviewed: bool


class Publication(BaseModel):
    id: str
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    source_url: Optional[str] = None


class Investigation(BaseModel):
    id: str
    source_id: str
    title: str
    acronym: Optional[str] = None
    summary: Optional[str] = None
    research_area: Optional[str] = None
    project_type: Optional[str] = None
    platform: Optional[str] = None
    environment: Optional[str] = None
    hardware: Optional[str] = None
    fuel_classes: List[FuelClass]
    fuel_materials: List[str]
    topic_tags: List[str]
    measurement_types: List[str]
    conditions: List[ConditionParameter]
    files: List[FileRef]
    publications: List[Publication]
    source_url: str
    doi: Optional[str] = None
    source_updated_at: Optional[str] = None
    ingested_at: str
    data_status: DataStatus


class InvestigationListItem(Investigation):
    match_reasons: List[str]


class Paginated(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int


class InvestigationQuery(BaseModel):
    q: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    material: Optional[str] = None
    measurement: Optional[str] = None
    sort: Optional[Literal["relevance", "title"]] = None
    page: Optional[int] = None
    page_size: Optional[int] = None


class TopicCount(BaseModel):
    label: str
    count: int


class DashboardSummary(BaseModel):
    investigation_count: int
    file_count: int
    publication_count: int
    last_ingestion_date: str
    counts_by_topic: List[TopicCount]
    featured_ids: List[str]
    dataset_note: str


class FilterOptions(BaseModel):
    topics: List[str]
    platforms: List[str]
    materials: List[str]
    measurements: List[str]


class CompareCell(BaseModel):
    value: Optional[str] = None


class CompareRow(BaseModel):
    field: str
    cells: Dict[str, CompareCell]


class ComparableValue(BaseModel):
    investigation_id: str
    label: str
    value: float


class ComparableParameter(BaseModel):
    name: str
    unit: str
    values: List[ComparableValue]


class ComparedInvestigation(BaseModel):
    id: str
    title: str
    acronym: Optional[str] = None
    source_url: str


class CompareResponse(BaseModel):
    investigations: List[ComparedInvestigation]
    rows: List[CompareRow]
    comparable_parameters: List[ComparableParameter]
    notes: List[str]


class CoverageCell(BaseModel):
    row: str
    column: str
    count: int
    investigation_ids: List[str]


class CoverageResponse(BaseModel):
    row_dimension: str
    column_dimension: str
    rows: List[str]
    columns: List[str]
    cells: List[CoverageCell]
    method_notes: List[str]


class AiCitation(BaseModel):
    investigation_id: str
    title: str
    source_url: str


class AiAnswer(BaseModel):
    answer: str
    citations: List[AiCitation]
    limitations: List[str]
    follow_up_questions: List[str]


class AiSearchIntent(BaseModel):
    interpreted_as: InvestigationQuery
    explanation: str


# ---------- Request bodies of the frontend's POST routes (api.ts) ----------


class CompareRequest(BaseModel):
    investigation_ids: List[str]


class AiSearchRequest(BaseModel):
    question: str


class AiAskRequest(BaseModel):
    question: str
    investigation_ids: Optional[List[str]] = None


# ---------- New shapes for the proposed changes (not in types.ts yet) ----------


class TestRow(BaseModel):
    """One test of one investigation, taken from its PSI Experimental Table."""

    id: str
    investigation_id: str
    test_label: Optional[str] = None  # the name of the test in the PSI table
    fuel: Optional[str] = None
    geometry: Optional[str] = None
    oxygen_pct: Optional[float] = None  # % by volume
    pressure_kpa: Optional[float] = None
    flow_cm_s: Optional[float] = None
    diluent: Optional[str] = None
    outcome: Optional[str] = None
    source_file: Optional[str] = None
    source_row: Optional[int] = None
    raw: Dict[str, Optional[str]]  # the row as it stands in the PSI table
    flags: List[str] = Field(default_factory=list)  # ingest warning tags (T2)
    data_status: DataStatus


class Habitat(BaseModel):
    id: str
    name: str
    oxygen_pct_min: Optional[float] = None
    oxygen_pct_max: Optional[float] = None
    pressure_kpa_min: Optional[float] = None
    pressure_kpa_max: Optional[float] = None
    gravity: Optional[str] = None
    citation: SourceCitation
    data_status: DataStatus


class ScorePart(BaseModel):
    name: str
    value: Optional[float] = None
    note: Optional[str] = None


class RankedInvestigation(BaseModel):
    investigation_id: str
    title: str
    acronym: Optional[str] = None
    score: Optional[float] = None
    parts: List[ScorePart]
    # T4 extended fields (all optional so existing tests stay green)
    match: Optional[float] = None           # tests_full / tests_total
    coverage: Optional[float] = None        # (tests with both O2 and P) / tests_total
    tests_total: Optional[int] = None
    tests_full: Optional[int] = None
    tests_partial: Optional[int] = None
    tests_none: Optional[int] = None
    unconstrained: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class RankResponse(BaseModel):
    habitat: Habitat
    items: List[RankedInvestigation]
    formula: Optional[str] = None
    notes: List[str]
    # T4 added
    data_source: Optional[str] = None
    method_note: Optional[str] = None


class VariableSummary(BaseModel):
    field: str
    status: Literal["varied", "constant", "not_reported"]
    values: List[str]
    minimum: Optional[float] = None
    maximum: Optional[float] = None


class VariablesResponse(BaseModel):
    investigation_id: str
    test_count: int
    variables: List[VariableSummary]
    notes: List[str]


class Health(BaseModel):
    status: str


# ---------- Mapping files (task T6 writes them, task T2 reads the approved ones) ----------

# A column of a PSI table feeds one of these TestRow fields, or nothing.
MAPPING_TEXT_FIELDS = ("test_label", "fuel", "geometry", "diluent", "outcome")
# Number fields, with the units a source column may be in. T2 converts to the field's own unit.
MAPPING_UNITS = {
    "oxygen_pct": ("percent", "mole_fraction"),
    "pressure_kpa": ("kPa", "mmHg", "psi", "atm"),
    "flow_cm_s": ("cm/s", "mm/s", "m/s"),
}
MAPPING_TARGET_FIELDS = MAPPING_TEXT_FIELDS + tuple(MAPPING_UNITS)


class MappingColumn(BaseModel):
    """How one column of a PSI table is used."""

    model_config = ConfigDict(extra="forbid")

    source_column: str
    target_field: Optional[str] = None  # None: the column is not used
    unit: Optional[str] = None  # unit of the source column, for number fields only
    confidence: Optional[Literal["high", "medium", "low"]] = None
    note: Optional[str] = None

    @model_validator(mode="after")
    def _field_and_unit_agree(self):
        if self.target_field is None:
            if self.unit is not None:
                raise ValueError(f"{self.source_column!r} is not used, so it takes no unit")
            return self
        if self.target_field not in MAPPING_TARGET_FIELDS:
            raise ValueError(f"unknown target field {self.target_field!r}")
        allowed = MAPPING_UNITS.get(self.target_field)
        if allowed is None:
            if self.unit is not None:
                raise ValueError(f"{self.target_field} is text and takes no unit")
        elif self.unit not in allowed:
            raise ValueError(f"{self.target_field} needs one of the units: {', '.join(allowed)}")
        return self


class MappingFile(BaseModel):
    """One file per PSI table, in data/mappings/. T2 must use approved files only."""

    model_config = ConfigDict(extra="forbid")

    source_id: str  # the PSI id of the table, for example PSI-25; T2 finds the record through it
    source_file: str
    status: Literal["proposed", "approved"]
    proposed_by: str  # the model's name, or "hand"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    accepted_warnings: List[str] = Field(default_factory=list)
    columns: List[MappingColumn]

    @model_validator(mode="after")
    def _file_rules(self):
        names = [column.source_column for column in self.columns]
        twice = sorted({name for name in names if names.count(name) > 1})
        if twice:
            raise ValueError(f"a table column is listed twice: {', '.join(twice)}")
        targets = [column.target_field for column in self.columns if column.target_field is not None]
        shared = sorted({target for target in targets if targets.count(target) > 1})
        if shared:
            raise ValueError(f"two columns feed the same field: {', '.join(shared)}")
        if self.status == "approved":
            if not (self.approved_by or "").strip() or not self.approved_at:
                raise ValueError("an approved file needs the approver's name and the date")
            try:
                datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("approved_at must be a date and time, for example 2026-11-14T15:00:00Z") from None
        elif self.approved_by or self.approved_at:
            raise ValueError("a proposed file has no approver and no date")
        return self
