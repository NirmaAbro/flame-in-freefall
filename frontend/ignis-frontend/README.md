# IGNIS Front-end

Front-end for **IGNIS**, a NASA microgravity fire research discovery dashboard, built for the
[NASA Space Apps Challenge 2026 "Flame in Freefall"](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/).

IGNIS helps researchers **find** NASA combustion investigations, **compare** them side by side,
see **what the indexed evidence covers (and does not)**, and **ask an AI assistant** questions that are answered with citations.

> IGNIS is a research discovery prototype. It is not a fire-prediction system, not a flight-certified safety tool,
> and not a replacement for NASA engineering review.

**Status:** the front-end is complete and runs on **dummy data** (`src/lib/mock`). Switch one environment
variable when the FastAPI backend is ready (see [Connecting the real backend](#connecting-the-real-backend)).

---

## Contents

1. [Quick start](#quick-start)
2. [Tech stack](#tech-stack)
3. [Pages and features](#pages-and-features)
4. [Project structure](#project-structure)
5. [How data flows](#how-data-flows)
6. [Dummy data](#dummy-data)
7. [Connecting the real backend](#connecting-the-real-backend)
8. [API contract the UI expects](#api-contract-the-ui-expects)
9. [Scientific rules built into the UI](#scientific-rules-built-into-the-ui)
10. [Design system](#design-system)
11. [Common changes (recipes)](#common-changes-recipes)
12. [Accessibility and QA checklist](#accessibility-and-qa-checklist)
13. [Scripts](#scripts)
14. [Deployment](#deployment)
15. [Troubleshooting](#troubleshooting)
16. [Known limitations and next steps](#known-limitations-and-next-steps)

---

## Quick start

Requirements: **Node.js 18.18 or newer** (Node 20 recommended) and npm.

```bash
unzip ignis-frontend.zip
cd ignis-frontend
npm install
cp .env.example .env.local      # optional: defaults already use dummy data
npm run dev
```

Open <http://localhost:3000>.

Before you submit or demo, run:

```bash
npm run typecheck
npm run lint
npm run build
```

All three pass on the delivered code.

---

## Tech stack

| Purpose | Choice |
| --- | --- |
| Framework | Next.js 14 (App Router) + React 18 |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS 3 (tokens in `tailwind.config.ts`, shared classes in `src/app/globals.css`) |
| Charts | Recharts |
| Icons | lucide-react |
| Fonts | System fonts only (Georgia for headlines). No network font download, so builds work offline. |
| Data | `fetch` to the IGNIS backend, or built-in dummy data |

No UI component library is used on purpose: every component is a small file you can read and edit.

---

## Pages and features

The plan asks for five destinations. Each is one route.

| Route | File | What it does |
| --- | --- | --- |
| `/` Overview | `src/app/page.tsx` | Hero with search and example prompts, a visual of an Earth flame vs a microgravity flame, dataset snapshot (counts from the API), featured investigations, topic coverage chart, shortcuts. |
| `/explore` | `src/app/explore/page.tsx` | Keyword search, "Ask in plain language" (AI search), filters (topic, fuel/material class, platform, measurement type), sorting, pagination, result cards with match reasons, source links and Add to compare. State is stored in the URL. |
| `/investigations/[id]` | `src/app/investigations/[id]/page.tsx` | Detail view with tabs: Overview, Conditions & Methods, Data & Files, Publications, Provenance. Missing data shows "Not reported in indexed record". |
| `/compare` | `src/app/compare/page.tsx` | Field-by-field table for 2 to 4 records (works without AI), "differs" markers, charts only for values that share name and unit, optional AI explanation. |
| `/research-map` | `src/app/research-map/page.tsx` | Coverage matrix (topic by fuel class), topic chart, and a plain-language "how to read this map" section explaining what a gap means. |
| `/copilot` | `src/app/copilot/page.tsx` | Chat-style Q&A with suggested prompts, cited source cards, limitations and follow-up questions, plus error handling. |

Global elements (in `src/app/layout.tsx`):

- **Top navigation** with global search, "Sample data" badge (only when using dummy data), Ask Copilot button, and a mobile menu.
- **Compare tray** pinned to the bottom of the screen once a record is selected.
- **Provenance footer** linking to NASA PSI and the challenge page.

---

## Project structure

```
ignis-frontend/
├── .env.example                  Environment variables (copy to .env.local)
├── next.config.mjs               Next.js config
├── tailwind.config.ts            Design tokens: colours, fonts, animation
├── package.json                  Dependencies and scripts
└── src/
    ├── app/                      Routes (one folder per page)
    │   ├── layout.tsx            Shared layout: nav, footer, compare tray
    │   ├── globals.css           Tailwind layers + reusable classes (.panel .btn .chip .input .page)
    │   ├── page.tsx              Overview
    │   ├── explore/page.tsx
    │   ├── investigations/[id]/page.tsx
    │   ├── compare/page.tsx
    │   ├── research-map/page.tsx
    │   └── copilot/page.tsx
    ├── components/
    │   ├── layout/               TopNav, Footer, CompareTray
    │   ├── dashboard/            MetricCard, HeroFlames, FeaturedInvestigation, TopicChart
    │   ├── search/               SearchBar, FilterPanel, InvestigationCard, Pagination
    │   ├── investigation/        DetailTabs
    │   ├── compare/              ComparisonTable, ComparableChart
    │   ├── analytics/            CoverageMatrix
    │   ├── copilot/              ChatPanel
    │   ├── evidence/             SourceCitation (provenance line under a value)
    │   └── ui/                   States (loading/error/empty), PageHeader, ReportedValue
    ├── context/CompareContext.tsx  Selected-for-compare records (kept in sessionStorage)
    ├── hooks/useAsync.ts           Loading / error / data helper for API calls
    └── lib/
        ├── api.ts                  The ONLY file that talks to data (mock or real backend)
        ├── types.ts                API response types (snake_case, mirrors the backend JSON)
        ├── constants.ts            Shared text, URLs, limits, nav items, example prompts
        └── mock/
            ├── data.ts             Dummy investigations
            └── mockApi.ts          Fake backend logic (search, ranking, compare, coverage, AI)
```

Component files stay small and each has a comment at the top saying what it is for.

---

## How data flows

```
Page / component  ->  src/lib/api.ts  ->  mock/mockApi.ts   (NEXT_PUBLIC_USE_MOCK=true)
                                      ->  FastAPI backend   (NEXT_PUBLIC_USE_MOCK=false)
```

- Components never call `fetch` themselves. They call a function from `src/lib/api.ts`.
- `useAsync` (`src/hooks/useAsync.ts`) wraps a call and gives `{ data, loading, error }`. Every page shows loading, error and empty states.
- Explore keeps its query in the URL (`/explore?q=flame&topic=Fire%20suppression&page=2`), so a search can be shared and the browser back button works.
- The browser talks only to the IGNIS backend. It never calls NASA or Gemini directly, and no secret is ever placed in a `NEXT_PUBLIC_` variable.

---

## Dummy data

File: `src/lib/mock/data.ts` (14 records) and `src/lib/mock/mockApi.ts` (the fake backend).

The records come only from the public challenge description: BASS, BASS-II, Saffire, SAME, SAME-R, DAFT, FLEX, FLEX-2,
CFI, ACME BRE, ACME E-FIELD Flames, ACME CFI-G, SPICE and SLICE.

Important things to know:

- **These are samples, not verified PSI records.** Each `source_url` is the general PSI repository page, `source_id` values are placeholders, and every record has `data_status: "sample"` (the UI shows a "Sample data" badge).
- Fields the challenge text does not state are `null` on purpose (for example, platform for SAME), so you can see every "Not reported" state.
- The only numeric condition is CFI-G "maximum oxygen concentration 85 % O2", taken from the challenge text with its citation. Because only one record has it, the Compare page correctly shows "no chart" until two records share a parameter and unit. To see a chart while developing, add a second numeric `conditions` entry with the same `name` and `unit` to another record in `data.ts`.
- The mock AI (`askAi`) is **not** Gemini. It retrieves records by keyword and stitches their summaries together, so you can test the full UI (citations, limitations, follow-ups, errors).
- Counts on Overview and Research Map are calculated from the data, not hard-coded.

---

## Connecting the real backend

1. Start the FastAPI backend (default `http://localhost:8000`).
2. Create `.env.local`:

   ```env
   NEXT_PUBLIC_USE_MOCK=false
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   ```

3. Restart `npm run dev` (environment variables are read at start-up).
4. Make sure the backend allows CORS for the front-end origin (`http://localhost:3000`).

If a response does not match the UI, change the type in `src/lib/types.ts` first (TypeScript will then point to every
place that needs updating), then adjust `src/lib/api.ts` if the endpoint path differs.

### Endpoint mapping

| Front-end function (`src/lib/api.ts`) | Backend endpoint | Used by |
| --- | --- | --- |
| `getDashboardSummary()` | `GET /dashboard/summary` | Overview, Research Map |
| `getFilterOptions()` | `GET /filters` (not in the plan: add it, or build it from `GET /topics` and distinct values) | Explore filters |
| `listInvestigations(query)` | `GET /investigations?q&topic&platform&material&measurement&sort&page&page_size` | Explore |
| `getInvestigation(id)` | `GET /investigations/{id}` | Detail page, Overview featured |
| `compareInvestigations(ids)` | `POST /compare` body `{ "investigation_ids": [...] }` | Compare |
| `getCoverage()` | `GET /analytics/coverage` | Research Map |
| `aiSearch(question)` | `POST /ai/search` body `{ "question": "..." }` | Explore, "Ask in plain language" |
| `askAi(question, ids?)` | `POST /ai/ask` body `{ "question": "...", "investigation_ids": [...] }` | Copilot, Compare |

The plan also lists `GET /investigations/{id}/files`, `GET /topics` and `GET /health`. The detail response in this UI already
contains `files` and `publications`, so the files endpoint is not needed unless you prefer to load them separately.

---

## API contract the UI expects

The exact TypeScript types are in `src/lib/types.ts`. Summary of the important shapes:

**Search list** (`GET /investigations`)

```json
{
  "items": [
    {
      "id": "psi-record-001",
      "source_id": "...",
      "title": "Official investigation title",
      "acronym": "ABC",
      "summary": "Short source-grounded summary...",
      "research_area": "Combustion Science",
      "project_type": null,
      "platform": null,
      "environment": "Microgravity",
      "hardware": null,
      "fuel_classes": ["Solid"],
      "fuel_materials": [],
      "topic_tags": ["Material flammability"],
      "measurement_types": [],
      "conditions": [],
      "files": [],
      "publications": [],
      "source_url": "https://psi.nasa.gov/...",
      "doi": null,
      "source_updated_at": null,
      "ingested_at": "2026-11-12",
      "data_status": "verified",
      "match_reasons": ["title match", "topic tag match"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

**Compare** (`POST /compare`) returns `investigations`, `rows` (one per field, with a `cells` object keyed by investigation id),
`comparable_parameters` (only parameters with the same name and unit in 2+ records) and `notes`.

**Coverage** (`GET /analytics/coverage`) returns `rows`, `columns`, `cells` (`row`, `column`, `count`, `investigation_ids`) and `method_notes`.

**AI** (`POST /ai/ask`) returns `answer`, `citations` (each with `investigation_id`, `title`, `source_url`), `limitations` and `follow_up_questions`.

Conventions:

- Field names are **snake_case** (matches Pydantic).
- Missing data is **`null`**, never `""` or `0`.
- Every numeric condition carries `unit`, `context` and a `citation`.
- The front-end shows `source_url` links straight from the API. Do not hard-code scientific facts in components.

---

## Scientific rules built into the UI

These come from the implementation plan and are enforced in code, so keep them when you change things:

| Rule | Where it is enforced |
| --- | --- |
| Missing data is shown as "Not reported in indexed record", never zero | `ui/ReportedValue.tsx`, used by detail tabs and compare table |
| Every value can show its source next to it | `evidence/SourceCitation.tsx` (used for reported conditions) |
| Charts only for comparable values (same name and unit) | Backend returns `comparable_parameters`; `compare/ComparableChart.tsx` never converts units |
| Every chart has a title, axis labels, units and a "what is counted" line | `dashboard/TopicChart.tsx`, `compare/ComparableChart.tsx` |
| A gap means "no matching indexed record", not "no research exists" | `analytics/CoverageMatrix.tsx`, Research Map method section |
| Compare table is deterministic and visible without AI | `compare/ComparisonTable.tsx`; AI is an optional button |
| AI answers show sources, limitations and never predict fire risk | `copilot/ChatPanel.tsx`, page descriptions, mock limitations |
| Microgravity is not labelled lunar or Martian gravity | No partial-gravity column exists; matrix notes say partial-gravity data is not yet in PSI |
| App keeps working if the AI is unavailable | Errors are caught in `ChatPanel`; keyword search and compare are independent of AI |

---

## Design system

Direction: scientific mission control. Deep navy base, a warm "flame" accent for actions, and a cool "diffusion flame" blue for links and data.
The hero compares an Earth teardrop flame with a spherical microgravity flame, which is the core idea of the challenge.

Tokens (`tailwind.config.ts`):

| Token | Use |
| --- | --- |
| `space-950` to `space-100` | Backgrounds, panels, borders, text |
| `flame-300` to `flame-600` | Primary buttons, selected states, "differs" markers |
| `diffuse-300` to `diffuse-500` | Links, chart bars, matrix cells |
| `font-display` | Georgia serif for headlines and numbers |
| `font-sans` | System sans for everything else |

Reusable classes (`src/app/globals.css`): `.panel`, `.input`, `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.chip`, `.page`.
Change the look of all buttons or cards in one place there.

Motion: the only non-interactive animation is the slow "breathing" microgravity flame, and it is disabled when the user prefers reduced motion.

---

## Common changes (recipes)

**Change brand colours:** edit the `space`, `flame` and `diffuse` scales in `tailwind.config.ts`. Chart colours are hex values inside `TopicChart.tsx` and `ComparableChart.tsx`.

**Add a navigation item:** add an entry to `NAV_ITEMS` in `src/lib/constants.ts` and create `src/app/<route>/page.tsx`.

**Add a filter in Explore:**
1. Add the field to `InvestigationQuery` and `FilterOptions` in `types.ts`.
2. Add a row to the `FILTERS` array in `search/FilterPanel.tsx`.
3. Read it from the URL in `explore/page.tsx` (`query` object).
4. Add it to `matchesFilters` in `mock/mockApi.ts` (or to the backend).

**Add a row to the comparison table:** add a `row("Label", (i) => ...)` line in `compareInvestigations` in `mock/mockApi.ts`. The table renders any rows the API returns.

**Add a new dummy record:** add a `sample({ ... })` entry to `MOCK_INVESTIGATIONS` in `mock/data.ts`. Counts, filters, matrix and search update automatically. Add new topic names to `TOPICS` in the same file.

**Change the coverage matrix dimensions:** the API returns `rows` and `columns`; change them in `getCoverage` (mock) or on the backend. The component renders whatever it receives.

**Change the example prompts:** edit `EXAMPLE_PROMPTS` in `src/lib/constants.ts`.

**Change the compare limit:** edit `MIN_COMPARE` / `MAX_COMPARE` in `src/lib/constants.ts`.

**Show real titles in the compare tray with the real backend:** the tray currently looks up acronyms from dummy data. Store `{ id, label }` in `CompareContext` instead of only `id`, and pass the label from `toggle(...)` where Add to compare is clicked.

---

## Accessibility and QA checklist

Built in:

- Semantic landmarks (`header`, `nav`, `main`, `footer`, `aside`, `search` forms) and labelled inputs.
- Visible keyboard focus ring (`:focus-visible` in `globals.css`).
- Tabs use `role="tablist"`, `role="tab"`, `role="tabpanel"` and `aria-selected`.
- Tables use `scope` headers and captions; icon-only buttons have `aria-label`.
- Loading and error messages use `role="status"` / `role="alert"`; results use `aria-live`.
- Reduced-motion preference respected.
- Responsive layouts: mobile menu, horizontally scrollable tables, stacked columns on small screens.

Manual test before a demo (matches the plan's checklist):

- [ ] Overview numbers load, and match the number of records in Explore.
- [ ] Search "flame" returns ranked results with "Matched on" reasons.
- [ ] Filters combine, and Reset clears them. Pagination works (page size is 6).
- [ ] Open a record: all five tabs work, missing fields say "Not reported in indexed record".
- [ ] Add 2 to 4 records to compare: the 5th is blocked with a message. Compare table shows "differs" markers.
- [ ] Research Map cells with a count link back to Explore with filters applied.
- [ ] Copilot answers show sources; a nonsense question says "The indexed records do not establish this."
- [ ] Asking "is this material safe" adds the "cannot declare a material safe" limitation.
- [ ] Layout works at 375 px width and with keyboard only.

---

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Development server with hot reload on port 3000 |
| `npm run build` | Production build (also type-checks and lints) |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (Next.js core web vitals rules) |
| `npm run typecheck` | TypeScript check without building |

---

## Deployment

- **Vercel (simplest):** import the repo, set `NEXT_PUBLIC_USE_MOCK` and `NEXT_PUBLIC_API_BASE_URL` in project settings, deploy.
- **Anywhere with Node:** `npm run build && npm run start`.
- For a hackathon demo with dummy data, no environment variables are required.
- Remember: `NEXT_PUBLIC_` variables are visible in the browser. Keep the Gemini key and database credentials only on the backend.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `npm install` fails on old Node | Use Node 18.18+ (`node -v`). |
| Changed `.env.local` but nothing changed | Restart `npm run dev`. |
| "Request ... failed" errors with real backend | Check the backend is running, `NEXT_PUBLIC_API_BASE_URL` is correct, and CORS allows `http://localhost:3000`. |
| Explore shows nothing after setting filters | Click Reset. Filters are combined with AND. |
| Compare page is empty after refresh | Selection is kept in `sessionStorage` per browser tab. A new tab starts empty. |
| Build error about `useSearchParams` | Components using it must sit inside `<Suspense>` (see `explore/page.tsx` and `copilot/page.tsx`). |

---

## Known limitations and next steps

- Dummy data is a small sample and is not verified against PSI. Replace it through the backend.
- The optional **knowledge graph** (P2 in the plan) is not built. The Research Map is matrix and chart based. If you add it, create `components/analytics/KnowledgeGraph.tsx` and a section on `research-map/page.tsx`.
- The **scenario explorer** (P2) is not built; if you add it, it must show closest matching evidence and state it is not a validated fire prediction.
- The research-gap AI explanation (optional in the plan) is not wired. Add a button on Research Map that calls `askAi` with the sparse cells' counts.
- No automated UI tests yet. Good first targets: `ReportedValue`, `ComparisonTable` (differs marker) and `CoverageMatrix` (zero cells).
