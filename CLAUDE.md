# Housing Market Data Project

## Goal
Build a state-level panel dataset (2010–2024) linking US housing market indicators to population, income, and employment. Use it to analyze affordability, supply elasticity, and how macro variables drive housing prices across states.

## Stack
- **Python** managed with **`uv`** (uv 0.11.16, Python 3.14)
- `pandas`, `requests`, `fredapi`, `duckdb`, `pyarrow`, `xlrd`, `openpyxl`
- `altair`, `vega_datasets`, `marimo`, `jupyter`, `jupytext`
- `textual`, `python-dotenv` — ACS variable explorer TUI
- Install deps: `uv sync` (all deps in pyproject.toml)

## GitHub
https://github.com/hhm-gh/housing (public)

## Project structure
```
housing/
├── collect_census_acs.py   # ACS 1-yr housing variables (Census API)
├── collect_census_bps.py   # Building permits (Census BPS FTP flat files)
├── collect_census_pep.py   # Population estimates + domestic migration
├── collect_saipe.py        # Median income + poverty (Census SAIPE timeseries API)
├── collect_fhfa.py         # House Price Index (FHFA flat file download)
├── collect_bls.py          # LAUS unemployment rate (BLS API v2)
├── collect_fred.py         # 30-yr mortgage rate (FRED API)
├── assemble_panel.py       # Joins all sources into panel.parquet + panel.duckdb
├── collect_acs_catalog.py  # Fetches full ACS 1-yr variable catalog → data/acs_variables.parquet
├── browse_acs_catalog.py   # Textual TUI: browse catalog, preview live data, mark/export variables
├── analysis.ipynb          # Jupyter: curated charts (choropleth, time series, scatter)
├── analysis_nb.py          # Jupytext source for analysis.ipynb
├── analysis.py             # Marimo: same curated charts, reactive widgets
├── explore.py              # Marimo: open-ended explorer — any column × states × years
├── .env                    # API keys (gitignored)
└── data/                   # Output files (gitignored)
    ├── acs_variables.parquet  ← ACS 1-yr variable catalog (36k variables, 1,243 concepts)
    ├── acs_selection.txt      ← marked variable export from browser (optional)
    ├── acs_housing.parquet
    ├── saipe.parquet
    ├── pep_population.parquet
    ├── fhfa_hpi.parquet
    ├── bls_laus.parquet
    ├── bps_permits.parquet
    ├── fred_mortgage.parquet
    ├── panel.parquet        ← final assembled panel
    └── panel.duckdb         ← same data, queryable via DuckDB
```

## Datasets collected

| Theme | Indicator | Script | Source | Coverage |
|---|---|---|---|---|
| Housing | Median home value, rent, homeownership rate, vacancy rate | `collect_census_acs.py` | Census ACS 1-yr | 2010–2024 (no 2020) |
| Housing | Total + single-family building permits | `collect_census_bps.py` | Census BPS FTP | 2010–2024 |
| Housing | House Price Index (all-transactions) | `collect_fhfa.py` | FHFA flat file | 2010–2024 |
| Housing | 30-yr fixed mortgage rate | `collect_fred.py` | FRED MORTGAGE30US | 2010–2024 |
| Population | Total population, domestic migration | `collect_census_pep.py` | Census PEP | 2010–2024 |
| Income | Median household income, poverty rate | `collect_saipe.py` | Census SAIPE | 2010–2024 |
| Employment | Unemployment rate (annual avg of monthly) | `collect_bls.py` | BLS LAUS | 2010–2024 |

## Final panel schema (`data/panel.parquet`, 765 rows = 51 states × 15 years)

```
fips_state              str    2-digit FIPS code
state_name              str
state_abbr              str    postal abbreviation
year                    int    2010–2024

# Housing
median_home_value       float  ACS B25077 — 93.3% coverage (no 2020)
median_gross_rent       float  ACS B25064 — 93.3%
homeownership_rate      float  ACS B25003 — 93.3%
vacancy_rate            float  ACS B25002 — 93.3%
hpi_at_annual           float  FHFA all-transactions — 100%
permits_total_units     int    BPS — 100%
permits_1unit           int    BPS single-family — 100%

# Income
median_household_income float  SAIPE — 100%
poverty_rate            float  SAIPE — 100%

# Population
population              int    Census PEP — 100%
domestic_migration      float  Census PEP — 33% (2020–2024 only)

# Employment
unemployment_rate       float  BLS LAUS annual avg — 100%

# Macro
mortgage_rate_30yr      float  FRED MORTGAGE30US — 100% (national, not by state)

# Derived
affordability_ratio     float  median_home_value / median_household_income
rent_burden             float  median_gross_rent * 12 / median_household_income
permits_per_1000_pop    float  permits_total_units / population * 1000
```

## API keys (stored in .env, gitignored)
- `CENSUS_API_KEY` — https://api.census.gov/data/key_signup.html
- `FRED_API_KEY` — https://fred.stlouisfed.org/docs/api/api_key.html
- BLS API: no key needed (public tier: 25 series/request, 10 years/request)

## Running the pipeline
```bash
# Collect all sources (run once; each saves its own parquet to data/)
CENSUS_API_KEY=<key> uv run collect_census_acs.py
CENSUS_API_KEY=<key> uv run collect_saipe.py
CENSUS_API_KEY=<key> uv run collect_census_pep.py
uv run collect_fhfa.py
uv run collect_census_bps.py
uv run collect_bls.py
FRED_API_KEY=<key> uv run collect_fred.py

# Assemble into final panel
uv run assemble_panel.py
```

## Known gaps / future work
- **ACS 2020 missing**: Census never released 2020 ACS 1-year due to COVID data quality. Expected NaN for all ACS columns in 2020.
- **Domestic migration 2010–2019 missing**: The PEP 2019 vintage API doesn't expose migration components. Only available 2020–2024 via NST-EST flat file.
- **BLS QCEW wages not yet collected**: Originally planned; would add median weekly wages by state. Requires BLS series IDs per state × industry.
- **Mortgage rate is national**: FRED MORTGAGE30US doesn't vary by state. Useful as a time-series control variable and for payment-based affordability, but not for cross-state comparisons.

## Running the notebooks
```bash
uv run marimo edit analysis.py    # curated analysis (choropleth, HPI vs unemployment, scatter)
uv run marimo edit explore.py     # open-ended explorer (any column × states × year range)
uv run jupyter notebook analysis.ipynb
```

## Marimo gotchas
- Variables prefixed with `_` are cell-local — use unprefixed names for anything shared between cells
- Cell output must be the last bare expression — charts inside `if/else` blocks never render; use `mo.stop(condition, output)` for guards instead
- `mo.ui.dropdown(value=...)` must match an options key (the label), not the underlying value
- Does not always hot-reload on file save — restart with `Ctrl+C` + `uv run marimo edit <file>`

## Analysis layer (next steps)
- Affordability and rent burden trends by state
- Housing supply elasticity: permit growth vs. population/employment growth
- Cross-state regression: how well does employment/income predict HPI growth?
- Pre/post-COVID comparisons (2019 vs. 2021–2024)

## Next step when resuming
Notebooks are working. Use `explore.py` for ad-hoc investigation, `analysis.py` for the curated story.
To load the panel directly:
```python
import pandas as pd
panel = pd.read_parquet("data/panel.parquet")
# or via SQL
import duckdb
con = duckdb.connect("data/panel.duckdb")
con.execute("SELECT * FROM panel WHERE state_abbr = 'CA'").df()
```
