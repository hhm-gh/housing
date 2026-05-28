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
    return panel,


@app.cell
def _(vega_data):
    # Load topojson once — not inside reactive cells
    states_topo = vega_data.us_10m.url
    return states_topo,


@app.cell
def _(mo):
    mo.md("# US Housing Market Analysis")


# ── Chart 1: Affordability choropleth ────────────────────────────────────────

@app.cell
def _(mo):
    mo.md("## 1 — Affordability Ratio by State\nHome value ÷ household income. Slide to change year.")


@app.cell
def _(mo):
    year_slider = mo.ui.slider(start=2010, stop=2024, step=1, value=2024, label="Year")
    year_slider
    return year_slider,


@app.cell
def _(alt, panel, states_topo, year_slider):
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


# ── Chart 2: HPI vs unemployment ─────────────────────────────────────────────

@app.cell
def _(mo):
    mo.md("## 2 — House Price Index vs. Unemployment\nHPI indexed to 2010 = 100. Click legend to highlight a state.")


@app.cell
def _(mo, panel):
    _all = sorted(panel["state_abbr"].dropna().unique().tolist())
    state_select = mo.ui.multiselect(
        options=_all,
        value=["CA", "TX", "FL", "NY", "OH", "AZ"],
        label="States",
    )
    state_select
    return state_select,


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


# ── Chart 3: Supply vs price growth ──────────────────────────────────────────

@app.cell
def _(mo):
    mo.md("## 3 — Housing Supply vs. Price Growth\nEach point = one state-year. Drag to select; size = population.")


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


if __name__ == "__main__":
    app.run()
