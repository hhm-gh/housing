# ---
# jupyter:
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # US Housing Market Analysis
#
# State × year panel, 2010–2024 (51 states).
#
# **Charts**
# 1. Affordability ratio by state — four key years side by side
# 2. House Price Index vs. unemployment — click legend to highlight a state
# 3. Housing supply vs. price growth — drag to brush by year

# %%
import pandas as pd
import altair as alt
from vega_datasets import data as vega_data

alt.data_transformers.disable_max_rows()

panel = pd.read_parquet('data/panel.parquet')
panel['fips_int'] = panel['fips_state'].astype(int)
panel = panel.sort_values(['fips_state', 'year'])
panel['hpi_growth'] = panel.groupby('fips_state')['hpi_at_annual'].pct_change() * 100
panel = panel.reset_index(drop=True)

print(f'{panel.shape[0]} rows × {panel.shape[1]} cols')
panel.head(3)

# %% [markdown]
# ## Chart 1 — Affordability Ratio by State
# Home value ÷ household income. Higher values = less affordable.

# %%
states = alt.topo_feature(vega_data.us_10m.url, 'states')


def make_choropleth(year_val):
    df = panel[panel['year'] == year_val].copy()
    return (
        alt.Chart(states)
        .mark_geoshape(stroke='white', strokeWidth=0.5)
        .transform_lookup(
            lookup='id',
            from_=alt.LookupData(
                df, 'fips_int',
                ['affordability_ratio', 'state_name',
                 'median_home_value', 'median_household_income']
            )
        )
        .encode(
            color=alt.Color(
                'affordability_ratio:Q',
                scale=alt.Scale(scheme='orangered', domain=[2, 12]),
                title='Home Value / Income'
            ),
            tooltip=[
                alt.Tooltip('state_name:N', title='State'),
                alt.Tooltip('affordability_ratio:Q', format='.1f', title='Ratio'),
                alt.Tooltip('median_home_value:Q', format='$,.0f', title='Home Value'),
                alt.Tooltip('median_household_income:Q', format='$,.0f', title='Income'),
            ]
        )
        .project('albersUsa')
        .properties(width=330, height=200, title=str(year_val))
    )


(
    alt.vconcat(
        alt.hconcat(make_choropleth(2010), make_choropleth(2015)),
        alt.hconcat(make_choropleth(2019), make_choropleth(2024))
    )
    .properties(title='Affordability Ratio — Home Value ÷ Household Income')
    .configure_view(stroke=None)
    .configure_title(fontSize=14, anchor='start')
)

# %% [markdown]
# ## Chart 2 — House Price Index vs. Unemployment
# HPI indexed to 2010 = 100. Click a state in the legend to highlight it across both panels.

# %%
highlight_states = ['CA', 'TX', 'FL', 'NY', 'OH', 'AZ']
df_ts = panel[panel['state_abbr'].isin(highlight_states)].copy()

hpi_base = (
    df_ts[df_ts['year'] == 2010]
    .set_index('fips_state')['hpi_at_annual']
    .rename('hpi_base')
)
df_ts = df_ts.join(hpi_base, on='fips_state')
df_ts['hpi_indexed'] = df_ts['hpi_at_annual'] / df_ts['hpi_base'] * 100

sel = alt.selection_point(fields=['state_abbr'], bind='legend')

hpi_line = (
    alt.Chart(df_ts)
    .mark_line(point=True)
    .encode(
        x=alt.X('year:O', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('hpi_indexed:Q', title='HPI (2010 = 100)'),
        color=alt.Color('state_abbr:N', title='State'),
        opacity=alt.condition(sel, alt.value(1), alt.value(0.1)),
        tooltip=[
            'state_abbr:N', 'year:O',
            alt.Tooltip('hpi_indexed:Q', format='.0f', title='HPI Index'),
        ]
    )
    .add_params(sel)
    .properties(width=640, height=220, title='House Price Index (2010 = 100)')
)

unemp_line = (
    alt.Chart(df_ts)
    .mark_line(point=True, strokeDash=[5, 3])
    .encode(
        x=alt.X('year:O', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('unemployment_rate:Q', title='Unemployment (%)'),
        color=alt.Color('state_abbr:N'),
        opacity=alt.condition(sel, alt.value(1), alt.value(0.1)),
        tooltip=[
            'state_abbr:N', 'year:O',
            alt.Tooltip('unemployment_rate:Q', format='.1f', title='Unemployment %'),
        ]
    )
    .add_params(sel)
    .properties(width=640, height=180, title='Unemployment Rate (%)')
)

(
    alt.vconcat(hpi_line, unemp_line)
    .configure_legend(labelLimit=200)
    .configure_title(fontSize=13, anchor='start')
)

# %% [markdown]
# ## Chart 3 — Housing Supply vs. Price Growth
# Each point = one state-year. Drag to select a region; highlighted points share the selected years.
# Size encodes population.

# %%
df_sc = panel.dropna(subset=['permits_per_1000_pop', 'hpi_growth']).copy()
df_sc = df_sc[df_sc['year'] >= 2011]

brush = alt.selection_interval(encodings=['x', 'y'])

(
    alt.Chart(df_sc)
    .mark_circle(opacity=0.55)
    .encode(
        x=alt.X(
            'permits_per_1000_pop:Q',
            title='Permits per 1,000 Population',
            scale=alt.Scale(zero=False)
        ),
        y=alt.Y(
            'hpi_growth:Q',
            title='HPI Year-over-Year Growth (%)',
            scale=alt.Scale(zero=False)
        ),
        color=alt.condition(brush, 'year:O', alt.value('lightgrey')),
        size=alt.Size('population:Q', scale=alt.Scale(range=[30, 400]), legend=None),
        tooltip=[
            alt.Tooltip('state_abbr:N', title='State'),
            alt.Tooltip('year:O'),
            alt.Tooltip('permits_per_1000_pop:Q', format='.2f', title='Permits/1k Pop'),
            alt.Tooltip('hpi_growth:Q', format='.1f', title='HPI Growth %'),
            alt.Tooltip('unemployment_rate:Q', format='.1f', title='Unemployment %'),
        ]
    )
    .add_params(brush)
    .properties(
        width=700, height=430,
        title='Housing Supply vs. Price Growth — drag to select years — size = population'
    )
    .configure_title(fontSize=13, anchor='start')
)
