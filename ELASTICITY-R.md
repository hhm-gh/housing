# Elasticity Visualization — R/Quarto Implementation

## Overview

`elasticity.qmd` is a standalone Quarto document that reads `data/panel.parquet`,
fits per-state OLS models, and renders three visualizations to a self-contained HTML
file. It has no dependency on the Python pipeline beyond the parquet file.

## How to render

Open `elasticity.qmd` in RStudio and click **Render**, or from the terminal:

```bash
quarto render elasticity.qmd
# Output: elasticity.html (self-contained, no external assets)
```

## R packages

| Package | Purpose |
|---|---|
| `arrow` | Read `data/panel.parquet` via `read_parquet()` |
| `dplyr` | Data filtering, grouping, joining |
| `tidyr` | `nest()` / `unnest()` for per-group model fitting |
| `purrr` | `map_dbl()` to apply `lm()` across nested groups |
| `forcats` | `fct_reorder()` for sorted bar chart axes |
| `ggplot2` | All visualizations |
| `scales` | `scales::squish` — clamp out-of-domain values to color scale limits |
| `tigris` | US state shapefiles (`states(cb=TRUE)`); cached after first download |
| `sf` | Spatial data handling; `shift_geometry()` repositions AK and HI |
| `patchwork` | Side-by-side plot composition with `+` operator |
| `ggrepel` | Non-overlapping state labels in the scatter plot |

## Model fitting

Both models use the same pattern: `group_by` → `nest()` → `map_dbl()` → `select(!data)`.
No loops. One row per state in the output.

**Level-level (linear slope):**
```r
lm(permits_per_1000_pop ~ hpi_at_annual, data = d)
# coefficient: permits per HPI index point
```

**Log-log (elasticity):**
```r
lm(log(permits_per_1000_pop) ~ log(hpi_at_annual), data = d)
# coefficient β: % Δ permits per % Δ HPI
# β > 1 → supply outpaces price growth; β < 1 → supply lags
```

Log-log requires `permits_per_1000_pop > 0` (filters out any zero-permit rows before fitting).

## Color scale design

All three sections use `scale_fill_gradient2` / `scale_color_gradient2` with explicit
midpoints:

| Model | Midpoint | Interpretation |
|---|---|---|
| Linear | `midpoint = 0` | Neutral = no slope; blue = negative; orange = positive |
| Log-log | `midpoint = 1` | Neutral = unit elasticity; blue = inelastic; orange = elastic |

**Domain clamping:** `limits` is set to the 95th-percentile deviation from the midpoint,
and `oob = scales::squish` clamps outliers to the nearest limit color rather than
rendering them as `NA` grey. This prevents extreme states (ND oil-boom distortion)
from collapsing the color range for all other states.

```r
lin_lim <- quantile(abs(elasticity_linear$slope),       0.95, na.rm = TRUE)
ll_dev  <- quantile(abs(elasticity_loglog$coef - 1.0),  0.95, na.rm = TRUE)
```

## Geography

`tigris::states(cb = TRUE, resolution = "20m", year = 2022)` downloads Census
cartographic boundary shapefiles. `cb = TRUE` uses the simplified (coastline-clipped)
version; `resolution = "20m"` is sufficient for state-level maps and keeps file size
small.

`shift_geometry()` repositions Alaska and Hawaii below the contiguous US — standard
for US state maps. `tigris_use_cache = TRUE` prevents re-downloading on each render.

Territories (PR, GU, VI, MP, AS) are filtered out before joining. The join key is
`GEOID` (tigris) ↔ `fips_state` (panel) — both are 2-digit zero-padded FIPS strings.

## Layout

`patchwork` composes the side-by-side pairs with `p_left + p_right`. The scatter plot
stands alone. Per-section `fig.height` overrides the document default where needed
(bar charts use `fig.height=10` to fit all 51 states legibly).
