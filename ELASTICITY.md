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

## Implementation

Both models are implemented in `elasticity.qmd` (R/Quarto), which reads
`data/panel.parquet` and renders to `elasticity.html`. See `ELASTICITY-R.md` for
full implementation details.

### Model 1 — Linear (level–level)

```r
lm(permits_per_1000_pop ~ hpi_at_annual, data = d)
```

Fit per state via `group_by` → `nest()` → `map_dbl()`. The β₁ slope is in units of
permits per HPI index point — not directly comparable across models, and sensitive to
the HPI base period.

### Model 2 — Log-log (elasticity proper)

```r
lm(log(permits_per_1000_pop) ~ log(hpi_at_annual), data = d)
```

Same fitting pattern. β₁ is a unit-free elasticity: % Δ permits per % Δ HPI.
Rows with `permits_per_1000_pop ≤ 0` are dropped before fitting.

### Coefficient normalization

Raw coefficients from both models are normalized to [0, 1] before visualization:

```
x_norm = max(0, x) / max(max(0, x))
```

Negative coefficients (e.g., ND, whose oil-boom cycle distorts the time series) are
clamped to 0. This puts both models on a common scale so their choropleths and bar
charts are visually comparable. The unit-elasticity reference line (β = 1) is
repositioned to its normalized equivalent: `1 / max(β)`.

### Visualizations

Three sections in `elasticity.html`, all using a sequential grey → orange color scale
(`low = "grey92"`, `high = "#d6604d"`) with `limits = c(0, 1)`:

1. **Choropleths** — side-by-side US maps (linear left, log-log right); AK and HI
   shifted below the contiguous US via `tigris::shift_geometry()`
2. **Ranked bar charts** — all 51 states sorted by normalized coefficient; log-log
   chart includes a dashed reference line at the normalized position of β = 1
3. **Scatter** — log-log normalized β (x) vs. average permits per 1,000 pop (y),
   state labels via `ggrepel`; reveals whether high-elasticity states actually build more
