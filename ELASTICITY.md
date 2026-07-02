# Housing Supply Elasticity

## Definition

Housing supply elasticity measures how much new housing construction responds to price increases: the percentage change in housing supply (permits/units built) for a given percentage change in home prices.

- **High elasticity** (e.g., Houston, Phoenix): prices rise → builders quickly add supply → prices stabilize. Associated with flat land, permissive zoning, fast approvals.
- **Low elasticity** (e.g., San Francisco, NYC): prices rise → supply barely responds → prices keep rising. Associated with geographic constraints, strict zoning, slow approvals, NIMBYism.

## In this panel

A rough approximation using available columns:

```
permits_per_1000_pop ~ f(hpi_at_annual)
```

The `f(...)` notation means "some unspecified function of" — it leaves the functional form open. The tilde `~` means "is modeled as" / "depends on" (R formula convention).

The slope of this relationship — how much permit activity rises per unit of HPI growth — is a state-level elasticity estimate.

## Recommended specification

Log-log regression, run separately per state (or with state fixed effects):

```
log(permits_per_1000_pop) ~ log(hpi_at_annual)
```

The coefficient on `log(hpi_at_annual)` is the elasticity directly: a value of 0.5 means a 1% rise in HPI is associated with a 0.5% rise in permits. Coefficients are comparable across states.

## Nominal vs. real HPI

The FHFA all-transactions HPI in this panel is **nominal** — it tracks price changes without adjusting for inflation. It is a repeat-sales index (measures price changes on the same properties over time), so it controls for compositional shifts in what sells, but the appreciation it captures is in current dollars.

For real (inflation-adjusted) analysis, divide by CPI or the GDP deflator. This panel does not do that. When interpreting elasticity estimates, keep in mind that a period of high general inflation will mechanically inflate nominal HPI, potentially overstating the price signal that builders actually respond to.

## Functional form note

`y ~ f(x)` is general; common specializations:

| Form | Specification | Coefficient interpretation |
|---|---|---|
| Linear | `y ~ x` | Δy per unit Δx |
| Log-linear | `y ~ log(x)` | Δy per 1% Δx (÷ 100) |
| Log-log | `log(y) ~ log(x)` | % Δy per % Δx = elasticity |
| Polynomial | `y ~ x + x²` | Non-constant marginal effect |

Log-log is standard for elasticity estimation.

## Implementation plan

### Phase 1 — Linear approximation

Model `permits_per_1000_pop ~ hpi_at_annual` as a simple OLS regression per state. The slope coefficient is a linear elasticity estimate in units of permits per index point.

**Steps:**
1. Load `data/panel.parquet`
2. Drop rows missing `permits_per_1000_pop` or `hpi_at_annual`
3. For each state, fit `permits_per_1000_pop = β₀ + β₁ * hpi_at_annual` via OLS (e.g., `numpy.polyfit` or `statsmodels`)
4. Collect the β₁ slope per state into a summary dataframe
5. Visualize as a choropleth map: fill = β₁ slope, so high-elasticity states stand out geographically
6. Add a ranked bar chart of states by slope as a companion view

**Limitations to note:** slope is in mixed units (permits per index point), not directly comparable to log-log elasticities; sensitive to HPI base period.

---

### Phase 2 — Log-log regression (elasticity proper)

Model `log(permits_per_1000_pop) ~ log(hpi_at_annual)` per state. The slope is a unit-free elasticity: % change in permits per % change in HPI.

**Steps:**
1. Same data prep as Phase 1; additionally drop any rows where either variable is ≤ 0
2. Take `log` of both variables
3. Fit OLS per state: `log(permits) = β₀ + β₁ * log(hpi)`
4. β₁ is the elasticity coefficient; collect per state
5. Reuse Phase 1 choropleth and bar chart, now coloring by β₁ elasticity
6. Add a scatter plot: x = β₁ elasticity, y = average `permits_per_1000_pop`, labeled by state abbreviation — reveals whether high-elasticity states actually build more
7. Overlay a reference line at β₁ = 1 (unit elasticity: permits grow proportionally with prices)

**Target output:** a single Altair chart compound (choropleth + bar + scatter) added as a new section in `analysis.py`.
