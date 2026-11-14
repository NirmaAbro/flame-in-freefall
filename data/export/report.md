# T2 Ingest Report

Total test rows ingested: **403** (16 with flags)


## PSI-25  (129 rows)

| Field | Parsed | None |
|---|---|---|
| test_label | 129 | 0 |
| fuel | 129 | 0 |
| diluent | 0 | 129 |
| outcome | 0 | 129 |
| oxygen_pct | 129 | 0 |
| pressure_kpa | 0 | 129 |
| flow_cm_s | 0 | 129 |

## PSI-69  (274 rows)

| Field | Parsed | None |
|---|---|---|
| test_label | 274 | 0 |
| fuel | 274 | 0 |
| diluent | 0 | 274 |
| outcome | 274 | 0 |
| oxygen_pct | 274 | 0 |
| pressure_kpa | 273 | 1 |
| flow_cm_s | 0 | 274 |

## PSI-68  (parameter-space summary — 0 test rows loaded)

The raw file for PSI-68 contains 8 parameter-space rows (one row per fuel type, not per test run). No rows were added to the tests table or the CSV export. The investigation record is kept in `data/investigations.json` with a `summary` field quoting the parameter ranges as written in the source table.


## Flagged cells

| Investigation | Row | Field | Column | Reason |
|---|---|---|---|---|
| PSI-25 | 2 | data_quality | multiple | oxygen_pct (final O2): initial=22.20% final=1.60% — drop of 20.60 pp exceeds threshold 5.0 pp |
| PSI-25 | 4 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 21 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 22 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 36 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 47 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 48 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 52 | data_quality | multiple | Initial CO (ppm): value -2.0 is negative — data quality flag, raw value kept |
| PSI-25 | 71 | data_quality | multiple | Initial CO (ppm): value -3.0 is negative — data quality flag, raw value kept |
| PSI-25 | 96 | data_quality | multiple | oxygen_pct (final O2): initial=20.80% final=0.60% — drop of 20.20 pp exceeds threshold 5.0 pp |
| PSI-25 | 124 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 125 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 126 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 127 | data_quality | multiple | oxygen_pct (final O2): initial=20.70% final=0.90% — drop of 19.80 pp exceeds threshold 5.0 pp |
| PSI-25 | 127 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-25 | 129 | data_quality | multiple | Initial CO (ppm): value -1.0 is negative — data quality flag, raw value kept |
| PSI-69 | 114 | pressure_kpa | Ambient pressure; mmHg | pressure_kpa (Ambient pressure; mmHg): source reports 0.0 mmHg, physically implausible for a test condition; treated as not reported (raw value kept) |
