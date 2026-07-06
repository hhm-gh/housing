# US Housing Market Analysis

A state-level panel dataset (2010–2024) linking US housing market indicators to population, income, and employment — with interactive Marimo notebooks for exploration and analysis.

## What's in here

**Data pipeline** — 7 collection scripts pull from public APIs and flat files, assembling a clean panel of 765 rows (51 states × 15 years):

| Theme | Indicators | Source |
|---|---|---|
| Housing | Median home value, rent, homeownership rate, vacancy rate | Census ACS 1-yr |
| Housing | House Price Index | FHFA |
| Housing | Building permits (total + single-family) | Census BPS |
| Housing | 30-yr mortgage rate | FRED |
| Population | Total population, domestic migration | Census PEP |
| Income | Median household income, poverty rate | Census SAIPE |
| Employment | Unemployment rate | BLS LAUS |

**Derived columns:** `affordability_ratio` (home value ÷ income), `rent_burden` (annual rent ÷ income), `permits_per_1000_pop`

**Analysis notebooks (Python/Marimo):**
- `analysis.py` — Marimo: choropleth affordability map, HPI vs. unemployment time series, supply vs. price-growth scatter, housing supply elasticity (linear and log-log, side-by-side)
- `explore.py` — Marimo: open-ended explorer — any indicator × any states × any year range
- `analysis.ipynb` — Jupyter: static version of the curated charts

**ACS variable explorer (Python/Textual):**
- `collect_acs_catalog.py` — downloads the ACS variable catalog from the Census API (no key required); supports ACS 1-year and 5-year, any vintage year; output named `data/acs_variables_{survey}_{year}.parquet`
- `browse_acs_catalog.py` — keyboard-driven terminal UI for browsing the catalog, previewing live data by state/county/MSA, marking variables of interest, and exporting selections; see `ACS-EXPLORER.md` for full key reference

```bash
uv run collect_acs_catalog.py                      # ACS 1-year 2023 (default)
uv run collect_acs_catalog.py 2023 --survey acs5   # ACS 5-year 2023 (needed for tract/county)
uv run browse_acs_catalog.py                       # browse 1-year catalog
uv run browse_acs_catalog.py --survey acs5         # browse 5-year catalog
```

See `ACS-EXPLORER.md` for full implementation status and key bindings, `FINER-GEOMETRIES.md` for the roadmap to county/tract/block-group data.

**Elasticity visualization (R/Quarto):**
- `elasticity.qmd` — standalone Quarto document: per-state OLS elasticity estimates (level-level and log-log), rendered to `elasticity.html`; no Python dependency beyond `data/panel.parquet`
- See `ELASTICITY.md` for concept and model notes, `ELASTICITY-R.md` for implementation details

## Stack

- Python 3.14, managed with `uv`
- `pandas`, `pyarrow`, `duckdb` for data
- `altair`, `vega_datasets` for charts
- `marimo`, `jupyter`, `jupytext` for notebooks
- R + Quarto for elasticity visualization (`elasticity.qmd`): `ggplot2`, `tigris`, `sf`, `patchwork`, `ggrepel`

## Setup

```bash
# Install dependencies
uv sync

# Add API keys
cp .env.example .env   # then fill in CENSUS_API_KEY and FRED_API_KEY
```

API keys needed:
- [Census API key](https://api.census.gov/data/key_signup.html) — for ACS, SAIPE, PEP
- [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) — for mortgage rate
- BLS: no key required

## Running the pipeline

```bash
# Collect each source (saves parquet to data/)
uv run collect_census_acs.py
uv run collect_saipe.py
uv run collect_census_pep.py
uv run collect_fhfa.py
uv run collect_census_bps.py
uv run collect_bls.py
uv run collect_fred.py

# Assemble into final panel
uv run assemble_panel.py
```

## Running the notebooks

```bash
uv run marimo edit analysis.py    # curated analysis
uv run marimo edit explore.py     # open-ended explorer
uv run jupyter notebook analysis.ipynb
```

## Loading the data directly

```python
import pandas as pd
panel = pd.read_parquet("data/panel.parquet")

# or via SQL
import duckdb
con = duckdb.connect("data/panel.duckdb")
con.execute("SELECT * FROM panel WHERE state_abbr = 'CA'").df()
```

## Known gaps

- **ACS 2020 missing** — Census never released 2020 ACS 1-year due to COVID data quality issues
- **Domestic migration 2010–2019 missing** — PEP 2019 vintage API doesn't expose migration components
- **Mortgage rate is national** — FRED MORTGAGE30US doesn't vary by state

## Code quality

No static analysis or type checking is configured (no mypy, ruff, or similar). The codebase is exploratory/analytical in nature.
