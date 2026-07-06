# ACS Variable Explorer — Goals and Implementation Status

## Motivation

The existing pipeline (`collect_census_acs.py`, `assemble_panel.py`) collects a fixed six-variable subset of ACS data chosen to support an affordability index. That subset is intentional and stays unchanged. But it makes the project brittle for any analysis that needs different housing, demographic, or economic variables.

This initiative adds a general-purpose layer for discovering, browsing, and ultimately collecting arbitrary ACS variables — without replacing or disrupting the existing pipeline.

Lives in this project for now; may split into its own project once scope is clearer.

---

## Phases

### Phase 1 — Fetch and cache the ACS variable catalog ✓ COMPLETE

**Script**: `collect_acs_catalog.py`

**What it does**: Downloads the ACS 1-year variables manifest from the Census API and saves it locally as a structured parquet file. No API key required.

**Source**: `https://api.census.gov/data/{year}/acs/acs1/variables.json`

**Output**: `data/acs_variables.parquet` — columns: `name`, `label`, `concept`, `group`, `predicate_type`, `year`

**Result**: 36,721 variables across 1,243 concept groups (2023 ACS 1-year). Filters out geography/predicate-only entries.

**Output naming**: `data/acs_variables_{survey}_{year}.parquet` — one file per survey × year combination.

**Usage**:
```bash
uv run collect_acs_catalog.py                      # ACS 1-year 2023
uv run collect_acs_catalog.py 2022                 # ACS 1-year 2022
uv run collect_acs_catalog.py 2023 --survey acs5   # ACS 5-year 2023
uv run collect_acs_catalog.py 2022 --survey acs5   # ACS 5-year 2022
```

---

### Phase 1.5 — Textual TUI browser ✓ IMPLEMENTED

**Script**: `browse_acs_catalog.py`

**What it does**: A keyboard-driven terminal UI for browsing the cached catalog and previewing live data.

**Layout**:
- **Left pane**: scrollable, filterable list of ACS concept groups
- **Right pane**: variables within the selected concept — name + full label (with `!!` hierarchy cleaned to ` › `)
- **Footer strip**: metadata for the highlighted variable — group code, predicate type, concept, mark status

**Key interactions**:

| Key | Action |
|---|---|
| Type (left pane) | Filter concept list by name |
| Enter | Move focus from filter input to concept list |
| Arrow keys | Navigate within focused pane |
| Tab / Escape | Switch between concept list and variable table |
| Space | Mark / unmark highlighted variable (shown with ★) |
| `g` | Open theme picker — filter concept list by subject area |
| `t` | Toggle: all concepts (1,243) ↔ top-level only (901, refinements suppressed) |
| `f` | Open full-screen concept browser |
| `p` | Open live data preview for highlighted variable |
| `e` | Export marked variable names to `data/acs_selection.txt` |
| `q` | Quit |

Active mode is always shown in the header subtitle (marked count · theme or concept count).

**Theme picker** (`g` key):
- Full-screen overlay listing all subject-area themes with concept counts (see `ACS-CONCEPTS.md`)
- `(All themes)` at top clears the theme filter
- Active theme marked with `▶`
- Theme view always operates on top-level concepts (refinements suppressed)
- Escape with no selection keeps the current theme

**Refinement toggle** (`t` key):
- Suppresses demographic refinements — concepts whose trailing `(...)` matches a base concept in the catalog
- 342 concepts suppressed; 119 concepts with trailing parentheticals are kept because no base exists
- Inactive when a theme is selected (theme view is always top-level)

**Full-screen concept browser** (`f` key):
- Full-terminal overlay of the currently active concept list (respects theme and toggle state)
- Filter-as-you-type; status line shows match count
- Selecting a concept loads its variables and closes the overlay

**Preview panel** (`p` key):
- Fetches 2023 ACS 1-year data for the highlighted variable
- Geography selector: **State** / **County** (65k+ pop, ACS 1-yr) / **MSA/CBSA**
- Switching geography cancels any in-flight request and re-fetches
- Filter input narrows results by geography name in real time
- Sorted by value descending; non-numeric values at end
- Requires `CENSUS_API_KEY` in `.env`

**Export**: `data/acs_selection.txt` — one variable ID per line, sorted alphabetically

**Usage**:
```bash
uv run browse_acs_catalog.py                      # ACS 1-year 2023 (default)
uv run browse_acs_catalog.py --survey acs5        # ACS 5-year 2023
uv run browse_acs_catalog.py --year 2022          # ACS 1-year 2022
uv run browse_acs_catalog.py --survey acs5 --year 2022   # ACS 5-year 2022
```

---

### Phase 2 — R-based visualization (deferred)

**What**: R scripts / Quarto documents that read ACS data parquets and produce maps, time series, and other charts — following the same pattern as `elasticity.qmd` and `tracts_co_viewer.R`.

**Inputs**: Parquets fetched by a generalized collection script (to be designed; informed by what Phase 1.5 selection export produces).

**Geography**: Initially state-level (ACS 1-year); county-level via ACS 5-year once the county pipeline exists (see `FINER-GEOMETRIES.md`).

**Details deferred** until variable selection workflow is clearer.

---

## What stays unchanged

- `collect_census_acs.py` — fixed six-variable affordability subset, unchanged
- `assemble_panel.py` — assembles `panel.parquet`, unchanged
- All existing Marimo/Jupyter notebooks — unchanged

---

## Geography scope

The preview panel covers **flat geographies** only — those that support a single wildcard API fetch:

| Geography | `for=` parameter | Notes |
|---|---|---|
| State | `state:*` | All 51 |
| County | `county:*&in=state:*` | ~800 counties (65k+ pop, ACS 1-yr only) |
| MSA/CBSA | `metropolitan statistical area/micropolitan statistical area:*` | ~900 metros |

**Tract and block group are not supported** in the current preview — they require a two-step drill-down (state → county → fetch) and ACS 5-year data. Deferred to a later phase.

---

## Tract and block group geography — issues and options

Adding tract (~85k) and block group (~240k) support involves four distinct problems, each with options.

### 1. Survey type changes

Tracts and block groups are only covered by **ACS 5-year**, not ACS 1-year. This means:
- Different API endpoint: `acs/acs5` instead of `acs/acs1`
- Different (larger) variable catalog — needs a separate fetch and cache alongside `data/acs_variables.parquet`
- Data represents a 5-year rolling average (e.g., "2019–2023"), not a point-in-time annual estimate
- The ACS 2020 gap that affects the 1-year pipeline does not apply to 5-year (rolling window absorbs it)

### 2. API query structure — no national wildcard

The Census API does not support `for=tract:*&in=state:*` (all tracts nationwide in one request). Options:

| Approach | Requests | Complexity | Notes |
|---|---|---|---|
| **State-by-state loop** | ~52 | Low | `for=tract:*&in=state:06` — consistent with existing collection pattern; practical for tracts |
| **County-by-county loop** | ~3,200 | Medium | Required for block groups: `for=block group:*&in=state:06&in=county:037` |
| **Census bulk FTP** | 1 per state (zip) | High | Pre-built flat files; efficient but complex to parse; different format from API responses |

State-by-state API loop is the natural starting point — it matches the existing `collect_*.py` pattern and 52 requests is fast. Block groups require the county-by-county loop (thousands of requests; needs throttling and resumability).

### 3. Scale, suppression, and storage

| Geography | Rows (nationally) | Suppression risk |
|---|---|---|
| Tract | ~85,000 | Moderate — small areas with <5 observations suppressed |
| Block group | ~240,000 | High — many cells missing, especially income/poverty breakdowns |

Parquet handles sparse data efficiently; DuckDB is well-suited for querying at this scale. But variable selection becomes more important — collecting all 36k variables at tract level is impractical. The marked-variable export from the browser (`data/acs_selection.txt`) is the intended mechanism for targeted collection.

### 4. Browser preview UI — drill-down required

The current flat geography selector (State / County / MSA) cannot be extended to tracts and block groups because those queries require a parent hierarchy. A drill-down modal is needed:

- **Tract**: State → fetch tracts (`for=tract:*&in=state:XX`)
- **Block group**: State → County → fetch block groups (`for=block group:*&in=state:XX&in=county:YYY`)

This is a different modal flow from the current `PreviewModal` — a cascading selector rather than a simple dropdown. The two levels (tract, block group) could share a single parameterized drill-down screen.

### Data naming and organization

Catalog files (variable metadata) and actual data files follow a consistent `{type}_{survey}_{year}_{geography}.parquet` scheme readable by both Python and R:

```
data/
  # Variable catalogs — one-time fetch per survey × year
  acs_variables_acs1_2023.parquet
  acs_variables_acs5_2023.parquet

  # Actual datasets — values for selected variables (future)
  acs_data_acs1_2023_state.parquet        # 51 rows, all states
  acs_data_acs5_2023_county.parquet       # ~3,200 rows
  acs_data_acs5_2023_tract.parquet        # ~85,000 rows (all states concatenated)
  acs_data_acs5_2023_tract_CA.parquet     # per-state if too large to concatenate
  acs_data_acs5_2023_blockgroup_CA.parquet
```

R reads these via `read_parquet(path)` the same way it reads `panel.parquet` today. The filename is self-describing — no separate manifest needed.

### Practical sequencing

1. ~~Add ACS 5-year catalog fetch to `collect_acs_catalog.py`~~ — **done** (`--survey acs5` flag)
2. Add tract preview via state-by-state drill-down in the browser
3. Add a targeted tract collection script driven by `data/acs_selection.txt`
4. Block group follows the same pattern but at higher query volume

---

## Open questions

- Should the catalog cover multiple years (to track when variables were added/removed), or just the latest year?
- ACS 5-year catalog is a separate endpoint with a different (larger) variable set — include in Phase 1 or defer?
- Should the Phase 1.5 export produce a ready-to-run collection script stub, or just a list of variable IDs? (currently: IDs only)
- Tract/block-group preview would need a drill-down UI and ACS 5-year endpoint — scope for a future phase.
