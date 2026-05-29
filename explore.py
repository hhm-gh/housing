import marimo

__generated_with = "0.23.8"
app = marimo.App(width="wide")


@app.cell
def _():
    import pandas as pd
    import altair as alt
    import marimo as mo

    return alt, mo, pd


@app.cell
def _(pd):
    panel = pd.read_parquet("data/panel.parquet")
    return (panel,)


@app.cell
def _(mo):
    mo.md("""
    # Housing Panel Explorer
    """)
    return


@app.cell
def _(mo, panel):
    # Column picker — exclude identifier columns
    _exclude = {"fips_state", "state_name", "state_abbr", "year"}
    _cols = [c for c in panel.columns if c not in _exclude]

    labels = {
        "median_home_value":        "Median Home Value ($)",
        "median_gross_rent":        "Median Gross Rent ($/mo)",
        "homeownership_rate":       "Homeownership Rate",
        "vacancy_rate":             "Vacancy Rate",
        "hpi_at_annual":            "House Price Index (FHFA)",
        "permits_total_units":      "Building Permits — Total Units",
        "permits_1unit":            "Building Permits — Single Family",
        "median_household_income":  "Median Household Income ($)",
        "poverty_rate":             "Poverty Rate (%)",
        "population":               "Population",
        "domestic_migration":       "Net Domestic Migration",
        "unemployment_rate":        "Unemployment Rate (%)",
        "mortgage_rate_30yr":       "30-yr Mortgage Rate (%)",
        "affordability_ratio":      "Affordability Ratio (Value ÷ Income)",
        "rent_burden":              "Rent Burden (Annual Rent ÷ Income)",
        "permits_per_1000_pop":     "Permits per 1,000 Population",
    }

    column_picker = mo.ui.dropdown(
        options={labels.get(c, c): c for c in _cols},
        value="Affordability Ratio (Value ÷ Income)",
        label="Indicator",
    )
    return column_picker, labels


@app.cell
def _(mo, panel):
    _states = sorted(panel["state_abbr"].dropna().unique().tolist())
    state_picker = mo.ui.multiselect(
        options=_states,
        value=["CA", "TX", "FL", "NY", "OH"],
        label="States",
    )
    return (state_picker,)


@app.cell
def _(mo, panel):
    _years = sorted(panel["year"].unique().tolist())
    year_range = mo.ui.range_slider(
        start=_years[0],
        stop=_years[-1],
        step=1,
        value=[_years[0], _years[-1]],
        label="Year range",
    )
    return (year_range,)


@app.cell
def _(column_picker, mo, state_picker, year_range):
    mo.hstack(
        [column_picker, state_picker, year_range],
        gap=2,
        align="end",
    )
    return


@app.cell
def _(alt, column_picker, labels, mo, panel, state_picker, year_range):
    _col = column_picker.value
    _states = state_picker.value
    _y0, _y1 = year_range.value

    mo.stop(not _states, mo.md("*Select at least one state.*"))
    mo.stop(_col is None, mo.md("*Select an indicator.*"))

    _df = (
        panel[
            panel["state_abbr"].isin(_states)
            & panel["year"].between(_y0, _y1)
        ]
        [["state_abbr", "year", _col]]
        .dropna(subset=[_col])
        .copy()
    )

    _label = labels.get(_col, _col)
    _sel = alt.selection_point(fields=["state_abbr"], bind="legend")

    (
        alt.Chart(_df)
        .mark_line(point=alt.OverlayMarkDef(size=60))
        .encode(
            x=alt.X("year:O", axis=alt.Axis(labelAngle=0), title="Year"),
            y=alt.Y(f"{_col}:Q", title=_label),
            color=alt.Color("state_abbr:N", title="State"),
            opacity=alt.condition(_sel, alt.value(1), alt.value(0.1)),
            tooltip=[
                alt.Tooltip("state_abbr:N", title="State"),
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip(f"{_col}:Q", title=_label, format=",.2f"),
            ],
        )
        .add_params(_sel)
        .properties(
            width=820,
            height=460,
            title=f"{_label}  |  {_y0}–{_y1}",
        )
        .configure_title(fontSize=14, anchor="start")
        .configure_legend(labelLimit=300)
        .configure_point(size=60)
    )
    return


if __name__ == "__main__":
    app.run()
