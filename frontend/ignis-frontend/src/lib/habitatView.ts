/**
 * Turns the backend's /habitats and /rank responses into simple objects for the page.
 * If a field shows as "—" in the UI, add the backend's real field name to the matching list below.
 */
import type { Habitat, RankResponse } from "./types";

export interface HabitatOption {
  id: string;
  name: string;
  description: string | null;
}

export interface RankedRow {
  id: string;
  label: string;
  title: string | null;
  /** null means "no tests". It must never be shown as 0. */
  score: number | null;
  testsMatched: number | null;
  testsTotal: number | null;
}

export interface RankView {
  formula: string | null;
  rows: RankedRow[];
}

type Raw = Record<string, unknown>;

/** First key that exists and is not null. */
function pick(raw: Raw, keys: string[]): unknown {
  for (const key of keys) {
    if (raw[key] !== undefined && raw[key] !== null) return raw[key];
  }
  return null;
}
const asText = (v: unknown): string | null => (typeof v === "string" && v ? v : null);
const asNumber = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const asList = (v: unknown): Raw[] => (Array.isArray(v) ? (v as Raw[]) : []);

export function toHabitatOptions(habitats: Habitat[]): HabitatOption[] {
  const list = Array.isArray(habitats)
    ? (habitats as unknown as Raw[])
    : asList(pick(habitats as unknown as Raw, ["items", "habitats"]));
  return list.flatMap((raw) => {
    const id = asText(pick(raw, ["id", "slug", "key", "habitat"]));
    if (!id) return [];
    return [{
      id,
      name: asText(pick(raw, ["name", "label", "title"])) ?? id,
      description: asText(pick(raw, ["description", "summary"])),
    }];
  });
}

export function toRankView(response: RankResponse): RankView {
  const raw = response as unknown as Raw;
  const rows = asList(pick(raw, ["items", "ranking", "ranked", "results", "investigations"])).flatMap((r) => {
    const id = asText(pick(r, ["investigation_id", "id"]));
    if (!id) return [];
    return [{
      id,
      label: asText(pick(r, ["acronym", "name", "title"])) ?? id,
      title: asText(r.title),
      score: asNumber(r.score), // keep null as null
      testsMatched: asNumber(pick(r, ["tests_matched", "matching_tests", "n_matching", "matched"])),
      testsTotal: asNumber(pick(r, ["tests_total", "total_tests", "n_tests", "total"])),
    }];
  });
  return { formula: asText(pick(raw, ["formula", "formula_text", "scoring_formula", "method"])), rows };
}