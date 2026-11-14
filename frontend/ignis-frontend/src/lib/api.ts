/**
 * Single place where the front-end talks to data.
 *
 *  NEXT_PUBLIC_USE_MOCK=true  -> dummy data from src/lib/mock (default)
 *  NEXT_PUBLIC_USE_MOCK=false -> real IGNIS backend (FastAPI) at NEXT_PUBLIC_API_BASE_URL
 *
 * Endpoint paths follow the REST contract in the implementation plan (section 4).
 * The browser only ever calls the IGNIS backend, never NASA or Gemini directly.
 */
import * as mock from "./mock/mockApi";
import type {
  AiAnswer,
  AiSearchIntent,
  CompareResponse,
  CoverageResponse,
  DashboardSummary,
  FilterOptions,
  Investigation,
  InvestigationListItem,
  InvestigationQuery,
  Paginated,
} from "./types";

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Thin fetch wrapper: JSON in/out, readable errors. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed (${response.status}). Check that the backend is running.`);
  }
  return response.json() as Promise<T>;
}

/** Turns { a: 1, b: undefined } into "?a=1". Skips empty values. */
function toQueryString(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

// GET /dashboard/summary
export const getDashboardSummary = (): Promise<DashboardSummary> =>
  USE_MOCK ? mock.getDashboardSummary() : request("/dashboard/summary");

// GET /topics  (+ other filter values). Adjust to the real contract when the backend exposes it.
export const getFilterOptions = (): Promise<FilterOptions> =>
  USE_MOCK ? mock.getFilterOptions() : request("/filters");

// GET /investigations
export const listInvestigations = (
  query: InvestigationQuery,
): Promise<Paginated<InvestigationListItem>> =>
  USE_MOCK ? mock.listInvestigations(query) : request(`/investigations${toQueryString(query)}`);

// GET /investigations/{id}
export const getInvestigation = (id: string): Promise<Investigation> =>
  USE_MOCK ? mock.getInvestigation(id) : request(`/investigations/${encodeURIComponent(id)}`);

// POST /compare
export const compareInvestigations = (ids: string[]): Promise<CompareResponse> =>
  USE_MOCK
    ? mock.compareInvestigations(ids)
    : request("/compare", { method: "POST", body: JSON.stringify({ investigation_ids: ids }) });

// GET /analytics/coverage
export const getCoverage = (): Promise<CoverageResponse> =>
  USE_MOCK ? mock.getCoverage() : request("/analytics/coverage");

// POST /ai/search
export const aiSearch = (question: string): Promise<AiSearchIntent> =>
  USE_MOCK ? mock.aiSearch(question) : request("/ai/search", { method: "POST", body: JSON.stringify({ question }) });

// POST /ai/ask
export const askAi = (question: string, investigationIds?: string[]): Promise<AiAnswer> =>
  USE_MOCK
    ? mock.askAi(question, investigationIds)
    : request("/ai/ask", {
        method: "POST",
        body: JSON.stringify({ question, investigation_ids: investigationIds }),
      });
