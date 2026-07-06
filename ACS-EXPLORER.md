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

**Usage**:
```bash
uv run collect_acs_catalog.py          # defaults to 2023
uv run collect_acs_catalog.py 2022     # specific year
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
| Type (left pane) | Filter concept list |
| Enter | Move focus from filter input to concept list |
| `f` | Open full-screen concept browser (entire terminal, same filter behaviour) |
| Arrow keys | Navigate within focused pane |
| Tab / Escape | Switch between concept list and variable table |
| Space | Mark / unmark highlighted variable (shown with ★) |
| `p` | Open live data preview for highlighted variable |
| `e` | Export marked variable names to `data/acs_selection.txt` |
| `q` | Quit |

**Preview panel** (`p` key):
- Fetches 2023 ACS 1-year data for the selected variable
- Geography selector: **State** / **County** (65k+ pop, ACS 1-yr) / **MSA/CBSA**
- Switching geography clears and re-fetches; in-flight requests are cancelled
- Filter input narrows the results table by geography name in real time
- Sorted by value descending; non-numeric values placed at end
- Requires `CENSUS_API_KEY` in `.env`

**Full-screen concept browser** (`f` key):
- Pushes a full-terminal overlay listing all 1,243 concept groups
- Same filter-as-you-type behaviour as the sidebar
- Selecting a concept loads its variables in the main view and closes the overlay
- Status line shows match count while filtering

**Export**: `data/acs_selection.txt` — one variable ID per line, sorted alphabetically

**Usage**:
```bash
uv run browse_acs_catalog.py
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

## Open questions

- Should the catalog cover multiple years (to track when variables were added/removed), or just the latest year?
- ACS 5-year catalog is a separate endpoint with a different (larger) variable set — include in Phase 1 or defer?
- Should the Phase 1.5 export produce a ready-to-run collection script stub, or just a list of variable IDs? (currently: IDs only)
- Tract/block-group preview would need a drill-down UI and ACS 5-year endpoint — scope for a future phase.
