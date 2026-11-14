# Habitat Ranking Formula (T4)

> **Limitation notice:** This ranking is a research-discovery aid that shows
> how well the indexed test conditions overlap with a habitat's known oxygen
> and pressure ranges. It is **not a safety assessment** and must not be used
> as one.

---

## Purpose

`GET /api/v1/rank?habitat=<id>` answers the question: *"which NASA microgravity
combustion investigations collected data under conditions closest to this
habitat?"*  The score helps a researcher decide where to look first; it does
not say whether a material is safe to use in that habitat.

---

## Inputs

| Item | Source |
|---|---|
| **Habitat oxygen range** (`o2_min`, `o2_max`, % by volume) | Habitat record in the habitats table or fixture. Must come from a cited NASA source. |
| **Habitat pressure range** (`pressure_min_kpa`, `pressure_max_kpa`, kPa) | Same. |
| **Test rows** | The `tests` table rows whose `investigation_id` matches each investigation. |

Habitat bounds that are `null` are treated as unconstrained (no limit in that
direction). The response lists which dimensions were unconstrained in the
`unconstrained` array of each ranked item.

---

## Per-row classification

Each test row is classified into one of three categories:

| Category | Condition |
|---|---|
| **full** | `oxygen_pct` is known **and** in the habitat O₂ range **and** `pressure_kpa` is known **and** in the habitat pressure range |
| **partial** | `oxygen_pct` is known **and** in range **and** `pressure_kpa` is `null` (not reported) |
| **none** | anything else: oxygen unknown, oxygen out of range, or pressure known but out of range |

> **Why 0.5 for partial rows?**
>
> Several investigations — notably BASS and BASS-II — do not report chamber
> pressure in their PSI Experimental Tables. The fan-display values in those
> tables are dimensionless dial settings, not calibrated flow velocities. It
> would be wrong to exclude these experiments entirely: their oxygen conditions
> are well-documented and directly relevant to habitat fire safety. Giving
> partial rows a weight of 0.5 reflects that one of the two key dimensions is
> confirmed while the other cannot be evaluated from the available data.
> A row whose pressure **is** known but falls outside the habitat range scores
> zero — the data is present and contradicts the habitat, so no credit is given.

---

## Score formula

```
score = (tests_full + 0.5 × tests_partial) / tests_total
```

The result is a number in **[0, 1]**:

- `1.0` — every test row is a full match on both oxygen and pressure
- `0.5` — every test row matches on oxygen but pressure is not reported
- `0.0` — no test row matches on oxygen, or all oxygen-matching rows have
  known pressure that is out of range

**When `tests_total == 0`** (no rows in the indexed data for this investigation)
the score is `null`, never `0`. The `note` field explains why. Zero-test
investigations sort after all investigations that have a score.

---

## Additional per-item metrics

| Field | Meaning |
|---|---|
| `match` | `tests_full / tests_total` — share of rows that are a full match |
| `coverage` | Rows where **both** `oxygen_pct` and `pressure_kpa` are non-null, divided by `tests_total`. High coverage means the scoring is based on complete data. |
| `tests_full`, `tests_partial`, `tests_none` | Raw counts. |
| `unconstrained` | List of dimension names (`"oxygen_pct"`, `"pressure_kpa"`) where the habitat bound is null on **both** sides. |

---

## Sort order

1. `score` descending (higher score first)
2. `tests_full` descending (break ties by number of full matches)
3. `investigation_id` ascending (final alphabetic tie-break)

Investigations with `score = null` (zero test rows) always sort last. The
order is fully deterministic: the same input always produces the same ranking.

---

## Habitat ranges and cited sources

Every habitat record must carry a `citation` object with:
- `source_name` — name of the NASA document or standard
- `source_url` — URL to the primary source
- `location` — the specific section or table that states the range
- `accessed_at` — ISO date when the value was checked

Ranges that cannot be traced to a cited NASA source must not be added to the
habitats table.

---

## Limitations

- The ranking reflects only the test conditions that are **indexed in this
  database**. PSI investigations for which no Experimental Table has been
  ingested receive a score of `null`.
- Pressure is not reported for some investigations (BASS, BASS-II). Their
  scores are based on oxygen overlap only, weighted at 0.5.
- The indexed pressure values come from the ambient-chamber readings in each
  PSI table. Localised flame pressure is not measured.
- Oxygen values are the initial ambient composition at the start of each test.
  Composition may change during a test; final values are not used in the score.
- This is a data-discovery tool. Actual spacecraft fire safety is governed by
  NASA-STD-6001B and related standards; consult a certified safety engineer.
