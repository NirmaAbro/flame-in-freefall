/**
 * Mock implementation of the backend API (dummy data, runs in the browser).
 *
 * Every function here has the SAME signature as its real counterpart in
 * src/lib/api.ts, so switching to the FastAPI backend needs no UI changes.
 * It mimics the deterministic behaviour described in the plan: exact title /
 * acronym match first, then title, tags, summary, with match reasons.
 */
import type {
  AiAnswer,
  AiSearchIntent,
  CompareResponse,
  ComparableParameter,
  CoverageResponse,
  DashboardSummary,
  FilterOptions,
  Investigation,
  InvestigationListItem,
  InvestigationQuery,
  Paginated,
} from "@/lib/types";
import { FEATURED_IDS, FUEL_CLASSES, MOCK_INVESTIGATIONS, TOPICS } from "./data";

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms));

const unique = (values: (string | null)[]) =>
  Array.from(new Set(values.filter((v): v is string => Boolean(v)))).sort();

// ---------- Search ranking ----------

interface Scored {
  item: InvestigationListItem;
  score: number;
}

/** Deterministic scoring: exact title/acronym > title > tags > summary. */
function scoreInvestigation(inv: Investigation, q: string): Scored {
  const reasons: string[] = [];
  let score = 0;
  const needle = q.trim().toLowerCase();

  if (needle) {
    const title = inv.title.toLowerCase();
    const acronym = (inv.acronym ?? "").toLowerCase();

    if (needle === acronym || needle === title) {
      score += 100;
      reasons.push("exact title/acronym match");
    } else if (title.includes(needle) || (acronym && acronym.includes(needle))) {
      score += 50;
      reasons.push("title match");
    }
    if (inv.topic_tags.some((t) => t.toLowerCase().includes(needle))) {
      score += 30;
      reasons.push("topic tag match");
    }
    if (inv.measurement_types.some((m) => m.toLowerCase().includes(needle))) {
      score += 20;
      reasons.push("measurement match");
    }
    if ((inv.summary ?? "").toLowerCase().includes(needle)) {
      score += 10;
      reasons.push("summary match");
    }
    // Multi-word queries: fall back to matching individual words in title/tags/summary.
    if (score === 0) {
      const words = needle.split(/\s+/).filter((w) => w.length > 2);
      const haystack = [inv.title, inv.acronym, inv.summary, ...inv.topic_tags]
        .join(" ")
        .toLowerCase();
      const hits = words.filter((w) => haystack.includes(w));
      if (hits.length > 0) {
        score += hits.length * 5;
        reasons.push(`matched words: ${hits.join(", ")}`);
      }
    }
  }
  return { item: { ...inv, match_reasons: reasons }, score };
}

function matchesFilters(inv: Investigation, query: InvestigationQuery): boolean {
  if (query.topic && !inv.topic_tags.includes(query.topic)) return false;
  if (query.platform && inv.platform !== query.platform) return false;
  if (query.material && !inv.fuel_classes.includes(query.material as never)) return false;
  if (query.measurement && !inv.measurement_types.includes(query.measurement)) return false;
  return true;
}

// ---------- Endpoints ----------

export async function getDashboardSummary(): Promise<DashboardSummary> {
  await delay();
  return {
    investigation_count: MOCK_INVESTIGATIONS.length,
    file_count: MOCK_INVESTIGATIONS.reduce((n, i) => n + i.files.length, 0),
    publication_count: MOCK_INVESTIGATIONS.reduce((n, i) => n + i.publications.length, 0),
    last_ingestion_date: "2026-11-12",
    counts_by_topic: TOPICS.map((label) => ({
      label,
      count: MOCK_INVESTIGATIONS.filter((i) => i.topic_tags.includes(label)).length,
    })),
    featured_ids: FEATURED_IDS,
    dataset_note:
      "Sample dataset built from the public challenge description. Replace with verified PSI records.",
  };
}

export async function getFilterOptions(): Promise<FilterOptions> {
  await delay(100);
  return {
    topics: TOPICS,
    platforms: unique(MOCK_INVESTIGATIONS.map((i) => i.platform)),
    materials: FUEL_CLASSES,
    measurements: unique(MOCK_INVESTIGATIONS.flatMap((i) => i.measurement_types)),
  };
}

export async function listInvestigations(
  query: InvestigationQuery = {},
): Promise<Paginated<InvestigationListItem>> {
  await delay();
  const page = query.page ?? 1;
  const pageSize = query.page_size ?? 6;

  let scored = MOCK_INVESTIGATIONS.filter((i) => matchesFilters(i, query)).map((i) =>
    scoreInvestigation(i, query.q ?? ""),
  );
  if (query.q?.trim()) scored = scored.filter((s) => s.score > 0);

  scored.sort((a, b) =>
    query.sort === "title" || !query.q?.trim()
      ? a.item.title.localeCompare(b.item.title)
      : b.score - a.score || a.item.title.localeCompare(b.item.title),
  );

  const start = (page - 1) * pageSize;
  return {
    items: scored.slice(start, start + pageSize).map((s) => s.item),
    page,
    page_size: pageSize,
    total: scored.length,
  };
}

export async function getInvestigation(id: string): Promise<Investigation> {
  await delay();
  const found = MOCK_INVESTIGATIONS.find((i) => i.id === id);
  if (!found) throw new Error(`Investigation "${id}" was not found in the indexed records.`);
  return found;
}

export async function compareInvestigations(ids: string[]): Promise<CompareResponse> {
  await delay();
  const records = ids
    .map((id) => MOCK_INVESTIGATIONS.find((i) => i.id === id))
    .filter((i): i is Investigation => Boolean(i));

  const row = (field: string, read: (i: Investigation) => string | null) => ({
    field,
    cells: Object.fromEntries(records.map((i) => [i.id, { value: read(i) }])),
  });
  const list = (values: string[]) => (values.length ? values.join(", ") : null);

  // Numeric parameters are only comparable when name AND unit are identical.
  const byKey = new Map<string, ComparableParameter>();
  for (const inv of records) {
    for (const p of inv.conditions) {
      if (typeof p.value !== "number" || !p.unit) continue;
      const key = `${p.name}__${p.unit}`;
      const entry = byKey.get(key) ?? { name: p.name, unit: p.unit, values: [] };
      entry.values.push({ investigation_id: inv.id, label: inv.acronym ?? inv.title, value: p.value });
      byKey.set(key, entry);
    }
  }

  return {
    investigations: records.map((i) => ({
      id: i.id,
      title: i.title,
      acronym: i.acronym,
      source_url: i.source_url,
    })),
    rows: [
      row("Research area", (i) => i.research_area),
      row("Platform", (i) => i.platform),
      row("Gravity environment", (i) => i.environment),
      row("Hardware", (i) => i.hardware),
      row("Fuel class", (i) => list(i.fuel_classes)),
      row("Fuels / materials", (i) => list(i.fuel_materials)),
      row("Topics", (i) => list(i.topic_tags)),
      row("Measurement types", (i) => list(i.measurement_types)),
      row("Reported conditions", (i) =>
        list(i.conditions.map((c) => `${c.name}: ${c.value}${c.unit ? " " + c.unit : ""}`)),
      ),
      row("Linked files", (i) => (i.files.length ? String(i.files.length) : null)),
    ],
    comparable_parameters: Array.from(byKey.values()).filter((p) => p.values.length >= 2),
    notes: [
      "Values are shown exactly as stored. Missing values are 'not reported', never zero.",
      "Numeric charts appear only when two or more records report the same parameter in the same unit.",
    ],
  };
}

export async function getCoverage(): Promise<CoverageResponse> {
  await delay();
  const cells = TOPICS.flatMap((row) =>
    FUEL_CLASSES.map((column) => {
      const matches = MOCK_INVESTIGATIONS.filter(
        (i) => i.topic_tags.includes(row) && i.fuel_classes.includes(column),
      );
      return { row, column, count: matches.length, investigation_ids: matches.map((m) => m.id) };
    }),
  );
  return {
    row_dimension: "Research topic",
    column_dimension: "Fuel / material class",
    rows: TOPICS,
    columns: FUEL_CLASSES,
    cells,
    method_notes: [
      "Counts are records found in the indexed PSI subset (sample data in this prototype).",
      "Topics were tagged manually from each record's summary. Reviewer and method are stored with each tag in the real backend.",
      "A gap means 'no matching indexed record'. It does not mean no research exists anywhere.",
      "Partial-gravity (Moon / Mars) combustion data is not yet available in PSI, so no environment column implies it.",
    ],
  };
}

// ---------- AI (mock) ----------

export async function aiSearch(question: string): Promise<AiSearchIntent> {
  await delay(400);
  const lower = question.toLowerCase();
  const topic = TOPICS.find((t) => lower.includes(t.toLowerCase().split(" ")[0]));
  return {
    interpreted_as: { q: topic ? undefined : question, topic },
    explanation: topic
      ? `Mock interpretation: filtered by topic "${topic}".`
      : "Mock interpretation: used your question as a keyword search.",
  };
}

export async function askAi(question: string, investigationIds?: string[]): Promise<AiAnswer> {
  await delay(900);
  const pool = investigationIds?.length
    ? MOCK_INVESTIGATIONS.filter((i) => investigationIds.includes(i.id))
    : MOCK_INVESTIGATIONS;

  const lower = question.toLowerCase();
  // Naive keyword retrieval, a stand-in for the backend's PostgreSQL full-text search.
  const words = lower.split(/[^a-z0-9-]+/).filter((w) => w.length > 3);
  const hits = pool
    .map((inv) => {
      const text = [inv.title, inv.acronym, inv.summary, ...inv.topic_tags].join(" ").toLowerCase();
      const exact = inv.acronym && lower.includes(inv.acronym.toLowerCase()) ? 5 : 0;
      return { inv, score: exact + words.filter((w) => text.includes(w)).length };
    })
    .filter((h) => h.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((h) => h.inv);

  const limitations = [
    "This is a mock answer built from sample records, not a Gemini response.",
    "No partial-gravity (Moon / Mars) combustion data is indexed.",
  ];
  if (/\b(safe|risk|predict|certif)/.test(lower)) {
    limitations.push(
      "IGNIS cannot declare a material safe or predict spacecraft fire behaviour. It only summarises indexed evidence.",
    );
  }

  if (hits.length === 0) {
    return {
      answer: "The indexed records do not establish this. Try narrowing the question or browsing Explore.",
      citations: [],
      limitations,
      follow_up_questions: ["Which topic areas have the fewest indexed records?"],
    };
  }
  return {
    answer:
      `${hits.length} indexed record${hits.length > 1 ? "s" : ""} relate to your question. ` +
      hits.map((h) => `${h.acronym ?? h.title}: ${h.summary ?? "no summary in indexed record"}`).join(" "),
    citations: hits.map((h) => ({ investigation_id: h.id, title: h.title, source_url: h.source_url })),
    limitations,
    follow_up_questions: [
      "Would you like to compare these records side by side?",
      "What evidence is available about oxygen concentration?",
    ],
  };
}
