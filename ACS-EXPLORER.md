# ACS Variable Explorer — Goals and Plan

## Motivation

The existing pipeline (`collect_census_acs.py`, `assemble_panel.py`) collects a fixed six-variable subset of ACS data chosen to support an affordability index. That subset is intentional and stays unchanged. But it makes the project brittle for any analysis that needs different housing, demographic, or economic variables.

This initiative adds a general-purpose layer for discovering, browsing, and ultimately collecting arbitrary ACS variables — without replacing or disrupting the existing pipeline.

Lives in this project for now; may split into its own project once scope is clearer.

---

## Phases

### Phase 1 — Fetch and cache the ACS variable catalog (Python)

**What**: A script that downloads the ACS variables manifest from the Census API and saves it locally as a structured file.

**Source**: `https://api.census.gov/data/{year}/acs/acs1/variables.json` — no API key required. Each entry includes variable name (e.g., `B25077_001E`), label, concept group, universe, and predicate type.

**Output**: `data/acs_variables.parquet` — one row per variable, columns for name, label, concept, group, predicateType, and the year fetched.

**Scope**: Start with one representative year (e.g., 2023 ACS 1-year). Optionally extend to ACS 5-year catalog separately.

**Script**: `collect_acs_catalog.py`

---

### Phase 1.5 — Textual TUI browser (Python/Textual)

**What**: A terminal UI for browsing the cached catalog — metadata only, no data fetching.

**Layout**:
- **Left pane**: scrollable, filterable list of ACS concept groups (e.g., "HOUSING VALUE", "TENURE", "VACANCY STATUS")
- **Right pane**: variables within the selected concept — variable name + full label
- **Footer strip**: detail for the highlighted variable — group code, universe, predicate type, ACS survey availability

**Key interactions**:
- Type to filter concept groups (left pane)
- Arrow keys to navigate
- Spacebar to mark/unmark variables of interest
- Export key to save the marked selection (e.g., to a text file or stub `collect_acs_custom.py`)

**Out of scope for 1.5**: No data fetching, no charting, no API calls beyond what Phase 1 already cached.

**Script**: `browse_acs_catalog.py`

---

### Phase 2 — R-based visualization

**What**: R scripts / Quarto documents that read ACS data parquets and produce maps, time series, and other charts — following the same pattern as `elasticity.qmd` and `tracts_co_viewer.R`.

**Inputs**: Parquets fetched by a generalized collection script (to be designed; informed by what Phase 1.5 selection export produces).

**Geography**: Initially state-level (ACS 1-year); county-level via ACS 5-year once the county pipeline exists (see `FINER-GEOMETRIES.md`).

**Details deferred** until Phase 1 and 1.5 are complete and variable selection workflow is clearer.

---

## What stays unchanged

- `collect_census_acs.py` — fixed six-variable affordability subset, unchanged
- `assemble_panel.py` — assembles `panel.parquet`, unchanged
- All existing Marimo/Jupyter notebooks — unchanged

---

## Open questions

- Should the catalog cover multiple years (to track when variables were added/removed) or just the latest year?
- ACS 5-year catalog is a separate endpoint and much larger — include in Phase 1 or defer?
- Should the Phase 1.5 export produce a ready-to-run collection script, or just a list of variable IDs?
