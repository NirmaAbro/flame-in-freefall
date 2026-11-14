"""Data shapes of the API (the contract).

The first part mirrors frontend/ignis-frontend/src/lib/types.ts field by field.
If a shape changes, change types.ts and this file together.

Rule from the frontend: a missing value is None (JSON null), never "" or 0.
"""
from typing import Dict, Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Field

FuelClass = Literal["Solid", "Gas", "Liquid droplet", "Particulate / aerosol"]
DataStatus = Literal["sample", "verified"]

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


class RankResponse(BaseModel):
    habitat: Habitat
    items: List[RankedInvestigation]
    formula: Optional[str] = None
    notes: List[str]


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
