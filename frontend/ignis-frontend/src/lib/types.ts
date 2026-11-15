/**
 * API response types.
 *
 * Field names use snake_case on purpose: they mirror the JSON contract in the
 * implementation plan (section 4), so the FastAPI backend can return its
 * Pydantic models as-is. If the backend contract changes, change it HERE first.
 *
 * Rule from the plan: missing data is `null`, never an empty string or zero.
 * The UI renders `null` as "Not reported in indexed record".
 */

export type FuelClass =
  | "Solid"
  | "Gas"
  | "Liquid droplet"
  | "Particulate / aerosol";

/** Where a displayed fact comes from. Shown next to the value it supports. */
export interface SourceCitation {
  source_name: string;
  source_url: string;
  doi: string | null;
  /** page / table / section inside the source, when known */
  location: string | null;
  accessed_at: string; // ISO date
}

/** One experimental condition, e.g. oxygen concentration. Units always kept with value. */
export interface ConditionParameter {
  name: string;
  value: number | string;
  unit: string | null;
  context: string | null;
  citation: SourceCitation;
}

export interface FileRef {
  id: string;
  title: string;
  file_type: string;
  description: string | null;
  source_url: string;
  reviewed: boolean;
}

export interface Publication {
  id: string;
  title: string;
  authors: string | null;
  year: number | null;
  doi: string | null;
  source_url: string | null;
}

export interface Investigation {
  id: string;
  source_id: string;
  title: string;
  acronym: string | null;
  summary: string | null;
  research_area: string | null;
  project_type: string | null;
  platform: string | null;
  environment: string | null; // gravity description (microgravity / ground / partial gravity)
  hardware: string | null;
  fuel_classes: FuelClass[];
  fuel_materials: string[];
  topic_tags: string[];
  measurement_types: string[];
  conditions: ConditionParameter[];
  files: FileRef[];
  publications: Publication[];
  source_url: string;
  doi: string | null;
  source_updated_at: string | null;
  ingested_at: string;
  /** Indicates whether the source record is sample or verified data. */
  data_status: "sample" | "verified";
}

/** One row of the Explore list. */
export interface InvestigationListItem extends Investigation {
  match_reasons: string[];
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface InvestigationQuery {
  q?: string;
  topic?: string;
  platform?: string;
  material?: string; // fuel class
  measurement?: string;
  sort?: "relevance" | "title";
  page?: number;
  page_size?: number;
}

export interface TestQuery {
  investigation_id?: string;
  fuel?: string;
  outcome?: string;
  min_oxygen?: number;
  max_oxygen?: number;
  min_pressure_kpa?: number;
  max_pressure_kpa?: number;
  page?: number;
  page_size?: number;
}

export interface TestRow {
  id: string;
  investigation_id: string;
  test_label: string | null;
  fuel: string | null;
  geometry: string | null;
  oxygen_pct: number | null;
  pressure_kpa: number | null;
  flow_cm_s: number | null;
  diluent: string | null;
  outcome: string | null;
  source_file: string | null;
  source_row: number | null;
  raw: Record<string, string | null>;
  flags: string[];
  data_status: "sample" | "verified" | "parsed";
}

export interface Habitat {
  id: string;
  name: string;
  oxygen_pct_min: number | null;
  oxygen_pct_max: number | null;
  pressure_kpa_min: number | null;
  pressure_kpa_max: number | null;
  gravity: string | null;
  citation: SourceCitation;
  data_status: "sample" | "verified";
}

export interface ScorePart {
  name: string;
  value: number | null;
  note: string | null;
}

export interface RankedInvestigation {
  investigation_id: string;
  title: string;
  acronym: string | null;
  score: number | null;
  parts: ScorePart[];
}

export interface RankResponse {
  habitat: Habitat;
  items: RankedInvestigation[];
  formula: string | null;
  notes: string[];
}

export interface VariableSummary {
  field: string;
  status: "varied" | "constant" | "not_reported";
  values: string[];
  minimum: number | null;
  maximum: number | null;
}

export interface VariablesResponse {
  investigation_id: string;
  test_count: number;
  variables: VariableSummary[];
  notes: string[];
}

export interface Health {
  status: string;
}

export interface DashboardSummary {
  investigation_count: number;
  file_count: number;
  publication_count: number;
  last_ingestion_date: string;
  counts_by_topic: { label: string; count: number }[];
  featured_ids: string[];
  dataset_note: string;
}

/** Filter options shown in the Explore filter panel (only values that exist in data). */
export interface FilterOptions {
  topics: string[];
  platforms: string[];
  materials: string[];
  measurements: string[];
}

export interface CompareCell {
  /** null = "not reported" */
  value: string | null;
}

export interface CompareRow {
  field: string;
  /** keyed by investigation id */
  cells: Record<string, CompareCell>;
}

/** A numeric parameter that exists, with the same name AND unit, in 2+ selected records. */
export interface ComparableParameter {
  name: string;
  unit: string;
  values: { investigation_id: string; label: string; value: number }[];
}

export interface CompareResponse {
  investigations: {
    id: string;
    title: string;
    acronym: string | null;
    source_url: string;
  }[];
  rows: CompareRow[];
  comparable_parameters: ComparableParameter[];
  notes: string[];
}

export interface CoverageCell {
  row: string;
  column: string;
  count: number;
  investigation_ids: string[];
}

export interface CoverageResponse {
  row_dimension: string;
  column_dimension: string;
  rows: string[];
  columns: string[];
  cells: CoverageCell[];
  method_notes: string[];
}

export interface AiCitation {
  investigation_id: string;
  title: string;
  source_url: string;
}

export interface AiAnswer {
  answer: string;
  citations: AiCitation[];
  limitations: string[];
  follow_up_questions: string[];
}

/** Result of "Ask in plain language" search: structured filters, validated by the backend. */
export interface AiSearchIntent {
  interpreted_as: InvestigationQuery;
  explanation: string;
}
