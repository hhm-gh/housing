# ACS Variable Concepts — High-Level Overview

## Source

This overview applies to the **American Community Survey (ACS) 1-year estimates**, variable catalog for **2023**, fetched from:

```
https://api.census.gov/data/2023/acs/acs1/variables.json
```

- **Survey**: ACS 1-year (published annually; requires 65,000+ population geography)
- **Publisher**: U.S. Census Bureau
- **Coverage**: States, large counties, MSAs/CBSAs, congressional districts, and other geographies meeting the 65k threshold
- **Catalog size**: 36,721 variables across 1,243 concept groups
- **Top-level concepts** (demographic refinements suppressed): 901
- **Local cache**: `data/acs_variables.parquet`

This catalog does **not** cover:
- **ACS 5-year estimates** — a separate, larger catalog covering all geographies including tracts and block groups (5-year rolling averages; less timely, more precise)
- **Decennial Census** — separate survey, published every 10 years (2010, 2020)
- **Other Census programs** — SAIPE, BPS, PEP, etc. are distinct from ACS

---

## Concept Themes (901 top-level concepts)

1. **Demographics & population** — Age, sex, race/ethnicity, nativity, citizenship status

2. **Income** — Household, family, and individual earnings; income by source (wages, Social Security, retirement, SSI, self-employment, dividends)

3. **Poverty** — Poverty status, ratio of income to poverty level, income deficit for families

4. **Housing stock** — Units in structure, rooms/bedrooms, year built, heating fuel, vacancy status

5. **Housing costs & affordability** — Gross rent, selected monthly owner costs, home value, rent-to-income ratio, cost burden

6. **Tenure & household structure** — Owner vs. renter, household size, family type, group quarters

7. **Employment & labor force** — Employment status, class of worker, industry, occupation, hours worked

8. **Commuting** — Means of transportation to work, travel time, time of departure, place of work

9. **Education** — Educational attainment, school enrollment, field of degree

10. **Health insurance** — Coverage type (employer, direct-purchase, Medicaid, Medicare, uninsured), by age and poverty status

11. **Disability** — Type (ambulatory, cognitive, hearing, vision, self-care, independent living), crosscut by age, poverty, and insurance status

12. **Language & immigration** — Language spoken at home, English proficiency, nativity of self and parents

13. **Family & living arrangements** — Marital status, presence/age of children, grandparents as caregivers, living alone

14. **Geographic mobility** — Who moved, where from (same county/state/abroad), by tenure and demographic

15. **Technology** — Computer ownership, internet subscription type, by age and household

---

## Structural concept types (cross-cutting, not separate themes)

Two categories appear across all themes above rather than forming their own subject area:

- **Allocation** (~100 concepts) — Data quality and imputation flags, one per main variable. Indicates what share of values were imputed rather than directly reported. Useful for assessing data quality but not substantive measures.

- **Aggregate & Median** (~135 concepts) — Aggregate sums and median values of the measures above (e.g., "Aggregate Household Income", "Median Gross Rent"). These are derived statistical forms of the underlying variables, not independent topics.

---

## Notes on demographic refinements

Many concepts appear in a base form plus multiple race/ethnicity-specific variants, e.g.:

```
Age of Householder by Household Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)
  └─ (American Indian and Alaska Native Alone Householder)
  └─ (Asian Alone Householder)
  └─ (Black or African American Alone Householder)
  └─ (Hispanic or Latino Householder)
  └─ (White Alone Householder)
  ... (9 refinements total)
```

The browser (`browse_acs_catalog.py`) detects these by checking whether stripping the trailing
parenthetical produces a concept that exists in the catalog. Press `t` to toggle between showing
all 1,243 concepts and the 901 top-level-only view.

342 concepts are suppressed in top-level-only mode. 119 concepts have trailing parentheticals
but are retained because no un-parenthesized base exists (the Census only published the
demographic breakdown, not an aggregate total).
