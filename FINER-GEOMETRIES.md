# Finer Geographies — Plan and Assessment

Extends the housing panel from state level down to county, MSA/CBSA, and eventually tract/block group. The state-level panel and elasticity viz are the baseline; this phase adds finer geographic resolution without breaking the existing pipeline.

## Recommended sequencing

1. **Collect county-level data** (Python)
2. **Assemble county panel** (Python)
3. **Generalize the R elasticity viz** to accept different geography levels
4. **Generalize `explore.py`** for dataset/geography selection

Start with county — it has the broadest data coverage, manageable scale (~3,200 rows/year vs. 51), and all existing indicators except FHFA HPI can be extended to it.

---

## Data availability by geography

| Indicator | County | MSA/CBSA | Tract | Block Group | Block |
|---|---|---|---|---|---|
| ACS housing vars (home value, rent, etc.) | ACS 5-yr | ACS 1-yr (large only) | ACS 5-yr | ACS 5-yr | No |
| House Price Index (FHFA) | No | Yes (all-transactions) | No | No | No |
| Building permits (BPS) | Yes (place/county) | Aggregable | No | No | No |
| Unemployment rate (BLS LAUS) | Yes | Yes | No | No | No |
| Median income / poverty (SAIPE) | Yes | No | No | No | No |
| Population (PEP) | Yes | No | No | No | No |
| Decennial Census counts | Yes | Yes | Yes | Yes | Yes |
| Mortgage rate (FRED) | National only | National only | National only | National only | National only |

**Key constraints:**
- ACS 1-year requires 65k+ population geography. Below that, use ACS 5-year (all geographies, but averages 5 years of data — less timely, more precise).
- FHFA HPI stops at MSA/CBSA. No tract-level HPI from a standard public source.
- Census suppresses small-cell counts at fine geographies. Expect significant missingness at tract and below.
- Block and block group data is practically limited to decennial years (2010, 2020) for most variables.

---

## FIPS / geography key hierarchy

| Geography | ID digits | Example | Approx count |
|---|---|---|---|
| State | 2 | `06` | 51 |
| County | 5 | `06037` (LA County) | 3,200 |
| MSA/CBSA | 5 (OMB codes, not FIPS) | `31080` (LA metro) | 390 |
| Census tract | 11 | `06037264100` | 85,000 |
| Block group | 12 | `060372641001` | 240,000 |
| Census block | 15 | `060372641001000` | 8M+ |

MSA/CBSA codes are **not FIPS** — they are OMB-defined CBSA codes. County-to-CBSA crosswalks are available from Census delineation files.

---

## Elasticity at finer geographies

The elasticity regression (`permits_per_1000_pop ~ hpi_at_annual`) does **not** use ACS data. It draws from:

- `permits_per_1000_pop` — BPS (building permits) + PEP (population)
- `hpi_at_annual` — FHFA House Price Index

The binding constraint is **FHFA HPI, which stops at MSA/CBSA** — no county-level HPI exists from a standard public source. So the finest geography the elasticity calculation can run at (as currently defined) is **MSA/CBSA**, not county.

Complication: PEP population is not available at MSA/CBSA level, so `permits_per_1000_pop` can't be constructed the same way. An MSA-level elasticity would need an alternative population denominator (e.g., aggregated county PEP, or decennial Census interpolated).

Implication for sequencing: county phase adds value for affordability and demographic analysis (ACS, SAIPE, BLS), but elasticity specifically requires the MSA/CBSA phase and extra work on the population denominator.

---

## Phase 1: County-level Python collection

New scripts needed (following existing pattern in `collect_*.py`):

| Script | Source | Notes |
|---|---|---|
| `collect_census_acs_county.py` | Census ACS 5-year | Same API, add `for=county:*&in=state:*` |
| `collect_saipe_county.py` | Census SAIPE | Same API, county endpoint already available |
| `collect_bls_county.py` | BLS LAUS | Series ID format changes at county level |
| `collect_fhfa_msa.py` | FHFA flat file | Different file from state-level HPI |
| `assemble_panel_county.py` | — | Joins county sources; must produce same derived columns as `assemble_panel.py` |

The derived columns (`permits_per_1000_pop`, `affordability_ratio`, `rent_burden`) are computed in `assemble_panel.py` and must be reproduced in the county assembler so downstream R code can rely on them.

---

## Phase 2: Generalize the R elasticity viz (`elasticity.qmd`)

Currently hard-coded to state-level in several places:

| Location | Hard-coded assumption | What changes at county level |
|---|---|---|
| Line 31 | `read_parquet("data/panel.parquet")` | Parameterize file path |
| Lines 37, 52 | `group_by(fips_state, state_name, state_abbr)` | Column names differ (`fips_county`, `county_name`, etc.) |
| Line 66 | `tigris::states(cb = TRUE, ...)` + `shift_geometry()` | Use `tigris::counties()` for county; `core_based_statistical_areas()` for MSA |
| Line 70–71 | Join key `GEOID = "fips_state"` | Changes per geography |
| Lines 80–126 | Bar charts labeled by `state_abbr` | Need equivalent short label per geography |
| Lines 135–154 | Scatter: `avg_permits` computed from `panel` | Must follow the parameterized panel source |

Approach options:
- **Quarto parameters** (`params:` in YAML front matter) — cleanest for a rendered report; pass `data_file` and `geography_level` as params
- **Separate `.qmd` files per geography** — simpler but duplicates logic
- **R helper functions** — extract the fit and plot logic into sourced `.R` functions, call from a thin `.qmd` wrapper

---

## Phase 3: Generalize `explore.py` (Marimo)

Currently hard-coded to `data/panel.parquet` (line 18). Needs:
- A file picker or geography-level dropdown to select which panel to load
- Possibly dynamic column handling if county/MSA panels have different column sets than the state panel

---

## Open questions

- Do county building permits map cleanly to county FIPS, or do BPS place-level permits need aggregation?
- ACS 5-year "vintage" years: which year label to use for a 5-year average (e.g., 2019–2023 ACS labeled as 2023)?
- How to handle the ACS 2020 gap at county level (same issue as state level)?
- Should the county panel replace or supplement the state panel in `explore.py`?
