# Housing Issues — Research Summary

Explores two questions at **census tract and block group geography**:
1. What correlates with homelessness?
2. What correlates with the rise in housing costs, both raw and as a fraction of income?

---

## Design constraint: tract/block group geography requires ACS 5-year

Tract and block group are only covered by **ACS 5-year** (not ACS 1-year). Each annual ACS 5-year release is a rolling 60-month average (e.g., the 2024 release = 2020–2024 data). This affects temporal resolution — estimates change slowly year-over-year — but provides complete geographic coverage down to block group (~240k nationally).

### Data availability at fine geographies

Most sources in the existing state-level panel do not publish at tract or block group level:

| Source | Tract | Block Group | Notes |
|---|---|---|---|
| ACS 5-year | ✓ | ✓ | Primary data source for this analysis |
| HUD CHAS (ACS-derived) | ✓ | ✗ | Income-adjusted cost burden; most recent vintage 2021 |
| Decennial Census | ✓ | ✓ | 2010 and 2020 only; limited variables |
| HUD AHAR PIT (homelessness counts) | ✗ | ✗ | CoC-level only; requires county-to-CoC crosswalk |
| BPS building permits | ✗ | ✗ | County/place level only |
| FHFA House Price Index | ✗ | ✗ | MSA/CBSA only |
| BLS LAUS (unemployment) | ✗ | ✗ | County level only |
| Census SAIPE (income/poverty) | ✗ | ✗ | County level only |
| Census PEP (population) | ✗ | ✗ | County level only |

**Implication:** at tract/block group level the analysis is almost entirely **ACS 5-year + HUD CHAS**. The other sources from the state-level panel have no equivalent at this resolution. The analytical variables below are all ACS 5-year unless otherwise noted.

---

## 1. What correlates with homelessness?

The strongest finding across the literature is that **community-level housing market factors dominate individual-level factors** as predictors of local homelessness rates. HUD's Homelessness Prediction Model identifies the big three community-level drivers:

**Rental costs → overcrowding → evictions** (roughly causal in sequence)

### ACS 5-year variables (available at tract and block group)

| Variable | ACS group | Notes |
|---|---|---|
| Median gross rent | B25064 | Strongest single predictor in urban areas |
| Rental vacancy rate | B25004 | Tight markets drive displacement |
| Overcrowding (>1 occupant/room) | B25014 | Direct precursor; also used to validate homeless estimates |
| Severe rent burden (>50% of income) | B25070 | Proxy for "doubled-up" hidden homelessness |
| Poverty rate | B17001 | Co-varies strongly with homelessness |
| Disability | B18101 | Strong individual-level predictor |
| Veteran status | B21001 | Disproportionate share of homeless population |
| Geographic mobility (moved in last year) | B07001 | Housing instability proxy |
| Race/ethnicity | B03002, B02001 | Black and Native American populations at 5–10× rates |

### Homelessness outcome data — geography limitation

ACS does not count homeless people (survey-missed). The correct outcome variable is **HUD's Annual Homeless Assessment Report (AHAR) Point-in-Time counts**, but these are published at the **Continuum of Care (CoC) level** — not tract or block group. Options:

- **County-level analysis**: join ACS tract predictors (aggregated to county) to HUD AHAR via HUD's county-to-CoC crosswalk. Loses tract-level resolution but gets a real outcome variable.
- **Tract-level risk mapping**: use ACS variables directly as risk proxies (cost burden, overcrowding, poverty, mobility) without a direct homeless count. Identifies high-risk tracts rather than modeling actual rates. Practically, this is the best available approach at tract level.
- **HUD Homelessness Prediction Model Dataset**: HUD publishes a combined dataset of ACS, eviction records, and climate variables that can serve as a reference for variable selection and model structure, even if the outcome is at CoC level.

---

## 2. What correlates with the rise in housing costs?

### 2a. Raw housing cost appreciation

Supply constraint effects are **asymmetric**: restrictions raise home prices by ~10 percentage points but rents by less than 5 points (SF Fed, 2025). Ownership affordability and rental affordability have different primary drivers.

**Supply-side variables (available at tract/block group via ACS 5-year):**

| Variable | ACS group | Notes |
|---|---|---|
| Rental vacancy rate | B25004 | Tightest single market predictor of price/rent growth |
| Total housing units | B25001 | Stock level; combine with decennial population for per-capita |
| Share single-family (low density) | B25024 | Density proxy; correlates with regulatory restriction |
| Median year structure built | B25035 | Older stock = less new construction |
| Homeownership rate | B25003 | High ownership correlates with NIMBY dynamics and supply restriction |

**Demand-side variables (available at tract/block group via ACS 5-year):**

| Variable | ACS group | Notes |
|---|---|---|
| Median household income | B19013 | Higher incomes bid up prices; also amenity sorting |
| Share of population 25–44 | B01001 | Peak renter / first-buyer cohort |
| Population | B01001 (total) | Demand-side; PEP not available at tract, use ACS |

**Not available at tract level:** FHFA HPI (the price outcome used in the state panel) stops at MSA/CBSA. At tract level, **ACS median home value (B25077) and median gross rent (B25064) become the price outcome variables** — levels rather than a transactions-based index.

**Rental vs. ownership:** vacancy rate and rent growth are the dominant rental-market variables. Supply constraints affect home prices more than rents — rental markets respond faster to new supply.

### 2b. Housing costs as a fraction of income (affordability)

#### HUD CHAS — the key data source (tract level, not block group)

The **Comprehensive Housing Affordability Strategy (CHAS)** dataset is a custom ACS tabulation published by HUD at the tract and county level, combining ACS microdata with HUD-adjusted Area Median Family Incomes (AMFIs). It gives cost burden counts broken down by:

- Income tier: ≤30%, 30–50%, 50–80%, 80–100%, >100% of AMFI
- Tenure: renter vs. owner-occupied
- Burden level: >30% and >50% of income spent on housing
- Housing quality: overcrowding, incomplete plumbing or kitchen

CHAS is more analytically useful than raw ACS B25070/B25071 because it answers "what share of *low-income* renters are severely burdened" rather than just the overall burden rate. It is not available at block group level.

**Access:** downloadable flat files by county and tract from [HUD USER](https://www.huduser.gov/portal/datasets/cp.html) and [HUD Open Data](https://hudgis-hud.opendata.arcgis.com/datasets/HUD::acs-5yr-chas-estimate-data-by-tract/about). Most recent vintage: 2021.

#### Raw ACS 5-year affordability variables (available at tract and block group)

| Variable | ACS group | Notes |
|---|---|---|
| Gross rent as % of household income (buckets) | B25070 | Renter cost burden: <10% through >50% |
| Median gross rent as % of household income | B25071 | Single summary statistic; directly comparable across tracts |
| Household income by gross rent as % of income | B25074 | Shows which income groups are burdened |
| Owner costs as % of income (buckets) | B25091 | Same structure for owners |
| Household income by owner costs as % of income | B25093 | Income-disaggregated owner burden |
| Gini coefficient | B19083 | Income inequality |
| Household income quintile upper limits | B19080–B19082 | Income distribution |
| Poverty rate | B17001 | Affordability worsens faster for lower-income households |

**Scale (2024):** 43.5 million households are cost-burdened (>30% of income on housing) — an all-time high per ACS estimates.

---

## Recommended analytical approach

### For homelessness risk mapping (tract level)

1. Pull ACS 5-year: B25004, B25014, B25070, B17001, B21001, B18101, B07001, B03002
2. Use ACS variables as risk proxies — no direct homeless count at tract level is publicly available
3. For county-level modeling with a real outcome: aggregate tract ACS predictors to county, join to HUD AHAR PIT counts via HUD's county-to-CoC crosswalk; use OLS or spatial regression (homelessness rates are highly spatially autocorrelated)

### For housing cost and affordability analysis (tract level)

1. **Outcome variables**: ACS B25064 (median rent) and B25077 (median home value) — these replace FHFA HPI, which doesn't exist at tract level
2. **Affordability burden**: HUD CHAS at tract level for income-adjusted cost burden; ACS B25070/B25071 where CHAS vintage is too old
3. **Supply-side regressors**: B25001 (units), B25024 (structure type), B25035 (age), B25004 (vacancy rate), B25003 (ownership rate)
4. **Demand-side regressors**: B19013 (income), B01001 (age structure and population)
5. **Temporal analysis**: use multiple ACS 5-year vintages (2015, 2016, … 2024); each is a rolling 5-year window — interpret changes slowly, not as year-over-year point-in-time

### Geography sequencing

County level first (manageable scale, all sources align, real homelessness outcome available), then tract (ACS 5-year + CHAS, risk mapping rather than regression against a homelessness count).

---

## Sources

- [Market Predictors of Homelessness — HUD USER](https://www.huduser.gov/portal/sites/default/files/pdf/Market-Predictors-of-Homelessness.pdf)
- [Homelessness Prediction Model Dataset & Research — HUD USER](https://www.huduser.gov/portal/datasets/hpmd.html)
- [2024 Annual Homelessness Assessment Report (AHAR) — HUD USER](https://www.huduser.gov/portal/datasets/ahar/2024-ahar-part-1-pit-estimates-of-homelessness-in-the-us.html)
- [Comprehensive Housing Affordability Strategy (CHAS) Data and Tables — HUD USER](https://www.huduser.gov/portal/datasets/cp.html)
- [ACS 5YR CHAS Estimate Data by Tract — HUD Open Data](https://hudgis-hud.opendata.arcgis.com/datasets/HUD::acs-5yr-chas-estimate-data-by-tract/about)
- [ACS 5YR CHAS Estimate Data by County — data.gov](https://catalog.data.gov/dataset/acs-5yr-comprehensive-housing-affordability-strategy-chas-estimate-data-by-county)
- [All That CHAS: Use Cases for the CHAS Dataset — HUD USER](https://www.huduser.gov/archives/portal/pdredge/pdr-edge-spotlight-article-012125.html)
- [Housing Unaffordability Soared to New Highs in 2024 — Harvard Joint Center for Housing Studies](https://www.jchs.harvard.edu/blog/housing-unaffordability-soared-new-highs-2024)
- [Housing Cost Burdens in 2024: In Brief — Congress.gov](https://www.congress.gov/crs-product/R48945)
- [Supply Constraints Do Not Explain House Price and Rent Differences — SF Fed, 2025](https://www.frbsf.org/wp-content/uploads/wp2025-06.pdf)
- [Housing Supply and Affordability: Evidence from Rents — Federal Reserve](https://www.federalreserve.gov/econres/feds/files/2020044pap.pdf)
- [Density Control, Home Price Appreciation, and Rental — Fannie Mae](https://www.fanniemae.com/media/48131/display)
- [Quantifying Doubled-Up Homelessness — NLIHC](https://nlihc.org/sites/default/files/Quantifying-Doubled-Up-Homelessness.pdf)
- [Homelessness Prediction Models in High-Income Countries: A Scoping Review — PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12621412/)
