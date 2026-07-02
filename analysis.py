import marimo

__generated_with = "0.23.8"
app = marimo.App(width="wide")


@app.cell
def _():
    import pandas as pd
    import altair as alt
    from vega_datasets import data as vega_data
    import marimo as mo

    return alt, mo, pd, vega_data


@app.cell
def _(pd):
    _raw = pd.read_parquet("data/panel.parquet")
    _raw["fips_int"] = _raw["fips_state"].astype(int)
    _raw = _raw.sort_values(["fips_state", "year"])
    _raw["hpi_growth"] = _raw.groupby("fips_state")["hpi_at_annual"].pct_change() * 100
    panel = _raw.reset_index(drop=True)
    return (panel,)


@app.cell
def _(vega_data):
    # Load topojson once — not inside reactive cells
    states_topo = vega_data.us_10m.url
    return (states_topo,)


@app.cell
def _(mo):
    mo.md("""
    # US Housing Market Analysis
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 1 — Affordability Ratio by State
    Home value ÷ household income. Slide to change year.
    """)
    return


@app.cell
def _(mo):
    year_slider = mo.ui.slider(start=2010, stop=2024, step=1, value=2024, label="Year")
    year_slider
    return (year_slider,)


@app.cell
def _(panel, states_topo, year_slider):
    import altair as _alt
    _df = panel[panel["year"] == year_slider.value].copy()

    _choropleth = (
        _alt.Chart(_alt.topo_feature(states_topo, "states"))
        .mark_geoshape(stroke="white", strokeWidth=0.5)
        .transform_lookup(
            lookup="id",
            from_=_alt.LookupData(
                _df, "fips_int",
                ["affordability_ratio", "state_name",
                 "median_home_value", "median_household_income"]
            )
        )
        .encode(
            color=_alt.Color(
                "affordability_ratio:Q",
                scale=_alt.Scale(scheme="orangered", domain=[2, 12]),
                title="Home Value / Income",
            ),
            tooltip=[
                _alt.Tooltip("state_name:N", title="State"),
                _alt.Tooltip("affordability_ratio:Q", format=".1f", title="Ratio"),
                _alt.Tooltip("median_home_value:Q", format="$,.0f", title="Home Value"),
                _alt.Tooltip("median_household_income:Q", format="$,.0f", title="Income"),
            ],
        )
        .project("albersUsa")
        .properties(
            width=720, height=430,
            title=f"Affordability Ratio — {year_slider.value}"
        )
        .configure_view(stroke=None)
        .configure_title(fontSize=14, anchor="start")
    )
    _choropleth
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2 — House Price Index vs. Unemployment
    HPI indexed to 2010 = 100. Click legend to highlight a state.
    """)
    return


@app.cell
def _(mo, panel):
    _all = sorted(panel["state_abbr"].dropna().unique().tolist())
    state_select = mo.ui.multiselect(
        options=_all,
        value=["CA", "TX", "FL", "NY", "OH", "AZ"],
        label="States",
    )
    state_select
    return (state_select,)


@app.cell
def _(alt, panel, state_select):
    _df = panel[panel["state_abbr"].isin(state_select.value)].copy()

    if _df.empty:
        import marimo as _mo
        _mo.md("*Select at least one state above.*")
    else:
        _base = (
            _df[_df["year"] == 2010]
            .set_index("fips_state")["hpi_at_annual"]
            .rename("hpi_base")
        )
        _df = _df.join(_base, on="fips_state")
        _df["hpi_indexed"] = _df["hpi_at_annual"] / _df["hpi_base"] * 100

        _sel = alt.selection_point(fields=["state_abbr"], bind="legend")

        _hpi = (
            alt.Chart(_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("year:O", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("hpi_indexed:Q", title="HPI (2010 = 100)"),
                color=alt.Color("state_abbr:N", title="State"),
                opacity=alt.condition(_sel, alt.value(1), alt.value(0.1)),
                tooltip=[
                    "state_abbr:N", "year:O",
                    alt.Tooltip("hpi_indexed:Q", format=".0f", title="HPI Index"),
                ],
            )
            .add_params(_sel)
            .properties(width=700, height=220, title="House Price Index (2010 = 100)")
        )

        _unemp = (
            alt.Chart(_df)
            .mark_line(point=True, strokeDash=[5, 3])
            .encode(
                x=alt.X("year:O", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("unemployment_rate:Q", title="Unemployment (%)"),
                color=alt.Color("state_abbr:N"),
                opacity=alt.condition(_sel, alt.value(1), alt.value(0.1)),
                tooltip=[
                    "state_abbr:N", "year:O",
                    alt.Tooltip("unemployment_rate:Q", format=".1f", title="Unemployment %"),
                ],
            )
            .add_params(_sel)
            .properties(width=700, height=180, title="Unemployment Rate (%)")
        )

        (
            alt.vconcat(_hpi, _unemp)
            .configure_legend(labelLimit=200)
            .configure_title(fontSize=13, anchor="start")
        )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3 — Housing Supply vs. Price Growth
    Each point = one state-year. Drag to select; size = population.
    """)
    return


@app.cell
def _(alt, panel):
    _df = panel.dropna(subset=["permits_per_1000_pop", "hpi_growth"]).copy()
    _df = _df[_df["year"] >= 2011]

    _brush = alt.selection_interval(encodings=["x", "y"])

    (
        alt.Chart(_df)
        .mark_circle(opacity=0.55)
        .encode(
            x=alt.X(
                "permits_per_1000_pop:Q",
                title="Permits per 1,000 Population",
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y(
                "hpi_growth:Q",
                title="HPI Year-over-Year Growth (%)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.condition(_brush, "year:O", alt.value("lightgrey")),
            size=alt.Size("population:Q", scale=alt.Scale(range=[30, 400]), legend=None),
            tooltip=[
                alt.Tooltip("state_abbr:N", title="State"),
                alt.Tooltip("year:O"),
                alt.Tooltip("permits_per_1000_pop:Q", format=".2f", title="Permits/1k Pop"),
                alt.Tooltip("hpi_growth:Q", format=".1f", title="HPI Growth %"),
                alt.Tooltip("unemployment_rate:Q", format=".1f", title="Unemployment %"),
            ],
        )
        .add_params(_brush)
        .properties(
            width=720, height=430,
            title="Housing Supply vs. Price Growth — drag to select years — size = population",
        )
        .configure_title(fontSize=13, anchor="start")
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4 — Housing Supply Elasticity
    Two OLS models fit per state across 2010–2024.
    - **Linear (level–level):** slope of `permits_per_1k_pop` on `hpi`. Units: permits per HPI index point.
    - **Log-log:** slope of `log(permits)` on `log(hpi)`. Coefficient β is a unit-free elasticity: % Δ permits per % Δ HPI. β > 1 means supply outpaces price growth; β < 1 means supply lags.
    """)
    return


@app.cell
def _(panel, pd):
    import numpy as _np

    _df = panel.dropna(subset=["permits_per_1000_pop", "hpi_at_annual"]).copy()
    _df_pos = _df[(_df["permits_per_1000_pop"] > 0) & (_df["hpi_at_annual"] > 0)].copy()

    _linear_rows, _loglog_rows = [], []

    for _fips, _grp in _df.groupby("fips_state"):
        if len(_grp) < 3:
            continue
        _meta = dict(
            fips_state=_fips,
            fips_int=int(_fips),
            state_name=_grp["state_name"].iloc[0],
            state_abbr=_grp["state_abbr"].iloc[0],
        )
        _slope_lin, _ = _np.polyfit(_grp["hpi_at_annual"], _grp["permits_per_1000_pop"], 1)
        _linear_rows.append({**_meta, "elasticity_slope": _slope_lin})

    for _fips, _grp in _df_pos.groupby("fips_state"):
        if len(_grp) < 3:
            continue
        _meta = dict(
            fips_state=_fips,
            fips_int=int(_fips),
            state_name=_grp["state_name"].iloc[0],
            state_abbr=_grp["state_abbr"].iloc[0],
        )
        _slope_ll, _ = _np.polyfit(
            _np.log(_grp["hpi_at_annual"]), _np.log(_grp["permits_per_1000_pop"]), 1
        )
        _loglog_rows.append({**_meta, "elasticity_coef": _slope_ll})

    elasticity_linear = (
        pd.DataFrame(_linear_rows)
        .sort_values("elasticity_slope", ascending=False)
        .reset_index(drop=True)
    )
    elasticity_loglog = (
        pd.DataFrame(_loglog_rows)
        .sort_values("elasticity_coef", ascending=False)
        .reset_index(drop=True)
    )
    return elasticity_linear, elasticity_loglog


@app.cell
def _(elasticity_linear, elasticity_loglog, states_topo):
    import altair as _alt

    def _make_choro(data, field, color_title, color_scale):
        return (
            _alt.Chart(_alt.topo_feature(states_topo, "states"))
            .mark_geoshape(stroke="white", strokeWidth=0.5)
            .transform_lookup(
                lookup="id",
                from_=_alt.LookupData(data, "fips_int", [field, "state_name", "state_abbr"]),
            )
            .encode(
                color=_alt.Color(
                    f"{field}:Q", scale=color_scale, title=color_title,
                    legend=_alt.Legend(orient="bottom"),
                ),
                tooltip=[
                    _alt.Tooltip("state_name:N", title="State"),
                    _alt.Tooltip("state_abbr:N", title="Abbr"),
                    _alt.Tooltip(f"{field}:Q", format=".4f", title=color_title),
                ],
            )
            .project("albersUsa")
            .properties(width=460, height=280)
        )

    _lin_max = float(elasticity_linear["elasticity_slope"].abs().quantile(0.95))
    _lin = _make_choro(
        elasticity_linear, "elasticity_slope", "Slope (permits / HPI pt)",
        _alt.Scale(scheme="blueorange", domain=[-_lin_max, 0.0, _lin_max]),
    ).properties(title="Linear: Level–Level OLS Slope")

    _ll_dev = float((elasticity_loglog["elasticity_coef"] - 1.0).abs().quantile(0.95))
    _ll = _make_choro(
        elasticity_loglog, "elasticity_coef", "β (% Δ permits / % Δ HPI)",
        _alt.Scale(scheme="blueorange", domain=[1.0 - _ll_dev, 1.0, 1.0 + _ll_dev]),
    ).properties(title="Log-Log: Elasticity Coefficient (β = 1 → unit elasticity)")

    (
        _alt.hconcat(_lin, _ll, spacing=24)
        .resolve_scale(color="independent")
        .configure_view(stroke=None)
        .configure_title(fontSize=12, anchor="start")
    )
    return


@app.cell
def _(alt, elasticity_linear, elasticity_loglog):
    def _make_bars(data, field, x_title, fmt, color_scale):
        return (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X(f"{field}:Q", title=x_title),
                y=alt.Y("state_abbr:N", sort="-x", title=None),
                color=alt.Color(f"{field}:Q", scale=color_scale, legend=None),
                tooltip=[
                    alt.Tooltip("state_name:N", title="State"),
                    alt.Tooltip(f"{field}:Q", format=fmt, title=x_title),
                ],
            )
            .properties(width=300, height=700)
        )

    _lin_max = float(elasticity_linear["elasticity_slope"].abs().quantile(0.95))
    _lin_bars = _make_bars(
        elasticity_linear, "elasticity_slope", "Slope (permits / HPI pt)", ".5f",
        alt.Scale(scheme="blueorange", domain=[-_lin_max, 0.0, _lin_max]),
    ).properties(title="Linear: Level–Level OLS Slope")

    _ll_dev = float((elasticity_loglog["elasticity_coef"] - 1.0).abs().quantile(0.95))
    _ll_bars = _make_bars(
        elasticity_loglog, "elasticity_coef", "Elasticity β", ".3f",
        alt.Scale(scheme="blueorange", domain=[1.0 - _ll_dev, 1.0, 1.0 + _ll_dev]),
    ).properties(title="Log-Log: Elasticity Coefficient")

    (
        alt.hconcat(_lin_bars, _ll_bars, spacing=40)
        .resolve_scale(color="independent")
        .configure_title(fontSize=12, anchor="start")
    )
    return


@app.cell
def _(alt, elasticity_loglog, panel, pd):
    _avg = (
        panel.dropna(subset=["permits_per_1000_pop"])
        .groupby("fips_state")["permits_per_1000_pop"]
        .mean()
        .reset_index()
        .rename(columns={"permits_per_1000_pop": "avg_permits"})
    )
    _scatter_df = elasticity_loglog.merge(_avg, on="fips_state")
    _ll_dev = float((_scatter_df["elasticity_coef"] - 1.0).abs().quantile(0.95))

    _pts = (
        alt.Chart(_scatter_df)
        .mark_circle(size=60, opacity=0.8)
        .encode(
            x=alt.X("elasticity_coef:Q", title="Log-Log Elasticity β",
                     scale=alt.Scale(zero=False)),
            y=alt.Y("avg_permits:Q", title="Avg Permits per 1,000 Pop (2010–2024)",
                     scale=alt.Scale(zero=False)),
            color=alt.Color("elasticity_coef:Q",
                            scale=alt.Scale(
                                scheme="blueorange",
                                domain=[1.0 - _ll_dev, 1.0, 1.0 + _ll_dev],
                            ),
                            legend=None),
            tooltip=[
                alt.Tooltip("state_name:N", title="State"),
                alt.Tooltip("elasticity_coef:Q", format=".3f", title="Elasticity β"),
                alt.Tooltip("avg_permits:Q", format=".2f", title="Avg Permits/1k Pop"),
            ],
        )
    )

    _labels = (
        alt.Chart(_scatter_df)
        .mark_text(dx=6, dy=-4, fontSize=9, align="left")
        .encode(
            x=alt.X("elasticity_coef:Q"),
            y=alt.Y("avg_permits:Q"),
            text="state_abbr:N",
        )
    )

    _rule = (
        alt.Chart(pd.DataFrame({"x": [1.0]}))
        .mark_rule(strokeDash=[5, 3], color="gray", strokeWidth=1)
        .encode(x=alt.X("x:Q", title=""))
    )

    (
        (_rule + _pts + _labels)
        .properties(
            width=620, height=420,
            title="Log-Log Elasticity vs. Avg Permits — do elastic states actually build more?",
        )
        .configure_title(fontSize=12, anchor="start")
    )
    return


if __name__ == "__main__":
    app.run()
