import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type {
  AiAnswer,
  AiSearchIntent,
  CompareResponse,
  CoverageResponse,
  DashboardSummary,
  FilterOptions,
  Habitat,
  Health,
  Investigation,
  InvestigationListItem,
  InvestigationQuery,
  Paginated,
  RankResponse,
  TestQuery,
  TestRow,
  VariablesResponse,
} from "./types";

const endpoints = {
  health: "/health",
  dashboard: "/dashboard/summary",
  filters: "/filters",
  investigations: "/investigations",
  investigation: (id: string) => `/investigations/${encodeURIComponent(id)}`,
  tests: "/tests",
  test: (id: string) => `/tests/${encodeURIComponent(id)}`,
  habitats: "/habitats",
  exportTests: "/export/tests.csv",
  rank: "/rank",
  variables: (id: string) =>
    `/investigations/${encodeURIComponent(id)}/variables`,
  compare: "/compare",
  coverage: "/analytics/coverage",
  aiSearch: "/ai/search",
  aiAsk: "/ai/ask",
} as const;

const client = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "https://flame-in-freefall-nyxr.onrender.com/api/v1",
  timeout: 15_000,
  headers: { Accept: "application/json", "Content-Type": "application/json" },
});

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem("ignis_access_token")
      : null;
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

client.interceptors.response.use(
  undefined,
  (error: AxiosError<{ detail?: string }>) => {
    const message = error.response?.data?.detail || error.message;
    return Promise.reject(
      new Error(message || "Unable to reach the IGNIS API."),
    );
  },
);

function get<T>(path: string, params?: object): Promise<T> {
  return client.get<T>(path, { params }).then(({ data }) => data);
}

function post<T>(path: string, body: unknown): Promise<T> {
  return client.post<T>(path, body).then(({ data }) => data);
}

export const getHealth = (): Promise<Health> => get(endpoints.health);

export const getDashboardSummary = (): Promise<DashboardSummary> =>
  get(endpoints.dashboard);

export const getFilterOptions = (): Promise<FilterOptions> =>
  get(endpoints.filters);

export const listInvestigations = (
  query: InvestigationQuery,
): Promise<Paginated<InvestigationListItem>> =>
  get(endpoints.investigations, query);

export const getInvestigation = (id: string): Promise<Investigation> =>
  get(endpoints.investigation(id));

export const listTests = (query: TestQuery = {}): Promise<Paginated<TestRow>> =>
  get(endpoints.tests, query);

export const getTest = (id: string): Promise<TestRow> =>
  get(endpoints.test(id));

export const getHabitats = (): Promise<Habitat[]> => get(endpoints.habitats);

export const exportTestsCsv = (
  query: Pick<TestQuery, "investigation_id"> = {},
): Promise<Blob> =>
  client
    .get<Blob>(endpoints.exportTests, { params: query, responseType: "blob" })
    .then(({ data }) => data);

export const rankInvestigations = (habitat: string): Promise<RankResponse> =>
  get(endpoints.rank, { habitat });

export const getInvestigationVariables = (
  id: string,
): Promise<VariablesResponse> => get(endpoints.variables(id));

export const compareInvestigations = (
  ids: string[],
): Promise<CompareResponse> =>
  post(endpoints.compare, { investigation_ids: ids });

export const getCoverage = (): Promise<CoverageResponse> =>
  get(endpoints.coverage);

export const aiSearch = (question: string): Promise<AiSearchIntent> =>
  post(endpoints.aiSearch, { question });

export const askAi = (
  question: string,
  investigationIds?: string[],
): Promise<AiAnswer> =>
  post(endpoints.aiAsk, {
    question,
    investigation_ids: investigationIds,
  });
