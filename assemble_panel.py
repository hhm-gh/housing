"""
Assemble all source parquet files into a single state × year panel dataset.
Outputs:
  data/panel.parquet   — analysis-ready flat file
  data/panel.duckdb    — queryable DuckDB database

Final schema:
  fips_state, state_name, state_abbr, year
  + housing:    median_home_value, median_gross_rent, homeownership_rate,
                vacancy_rate, hpi_at_annual, permits_total_units, permits_1unit
  + income:     median_household_income, poverty_rate
  + population: population, domestic_migration
  + employment: unemployment_rate
  + macro:      mortgage_rate_30yr
  + derived:    affordability_ratio, rent_burden, permits_per_1000_pop

Usage:
  uv run assemble_panel.py
"""

import pandas as pd
import duckdb
from pathlib import Path

DATA = Path("data")

FIPS_TO_ABBR = {
    "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT",
    "10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL",
    "18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD",
    "25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE",
    "32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND",
    "39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD",
    "47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV",
    "55":"WI","56":"WY",
}


def load() -> dict[str, pd.DataFrame]:
    return {
        "acs":   pd.read_parquet(DATA / "acs_housing.parquet"),
        "saipe": pd.read_parquet(DATA / "saipe.parquet"),
        "pep":   pd.read_parquet(DATA / "pep_population.parquet"),
        "fhfa":  pd.read_parquet(DATA / "fhfa_hpi.parquet"),
        "bls":   pd.read_parquet(DATA / "bls_laus.parquet"),
        "bps":   pd.read_parquet(DATA / "bps_permits.parquet"),
        "fred":  pd.read_parquet(DATA / "fred_mortgage.parquet"),
    }


def build_spine(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the canonical (fips_state, year) index from SAIPE — 51 states × 15 years."""
    saipe = tables["saipe"][["fips_state", "state_name"]].drop_duplicates()
    years = pd.DataFrame({"year": range(2010, 2025)})
    spine = saipe.merge(years, how="cross")
    spine["state_abbr"] = spine["fips_state"].map(FIPS_TO_ABBR)
    return spine.sort_values(["fips_state", "year"]).reset_index(drop=True)


def join_all(spine: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    key = ["fips_state", "year"]

    # ACS
    acs_cols = ["median_home_value", "median_gross_rent", "homeownership_rate", "vacancy_rate"]
    panel = spine.merge(tables["acs"][key + acs_cols], on=key, how="left")

    # FHFA
    panel = panel.merge(
        tables["fhfa"][key + ["hpi_at_annual"]],
        on=key, how="left",
    )

    # BPS
    bps_cols = ["permits_total_units", "permits_1unit"]
    panel = panel.merge(tables["bps"][key + bps_cols], on=key, how="left")

    # SAIPE
    saipe_cols = ["median_household_income", "poverty_rate"]
    panel = panel.merge(tables["saipe"][key + saipe_cols], on=key, how="left")

    # PEP — filter to known state FIPS before joining to avoid territory rows
    pep = tables["pep"][tables["pep"]["fips_state"].isin(FIPS_TO_ABBR)]
    pep_cols = ["population", "domestic_migration"]
    panel = panel.merge(pep[key + pep_cols], on=key, how="left")

    # BLS
    panel = panel.merge(
        tables["bls"][key + ["unemployment_rate"]],
        on=key, how="left",
    )

    # FRED — national series, join on year only
    panel = panel.merge(tables["fred"], on="year", how="left")

    return panel


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["affordability_ratio"] = df["median_home_value"] / df["median_household_income"]

    df["rent_burden"] = (df["median_gross_rent"] * 12) / df["median_household_income"]

    df["permits_per_1000_pop"] = (
        df["permits_total_units"] / df["population"] * 1000
    )

    return df


def coverage_report(df: pd.DataFrame) -> None:
    print("\nCoverage (% non-null by column):")
    total = len(df)
    indicator_cols = [c for c in df.columns if c not in ("fips_state", "state_name", "state_abbr", "year")]
    for col in indicator_cols:
        pct = df[col].notna().sum() / total * 100
        bar = "#" * int(pct / 5)
        print(f"  {col:<30s} {pct:5.1f}%  {bar}")


def main():
    print("Loading source files...")
    tables = load()

    print("Building spine (51 states × 2010-2024)...")
    spine = build_spine(tables)
    print(f"  {len(spine)} rows")

    print("Joining all tables...")
    panel = join_all(spine, tables)

    print("Computing derived indicators...")
    panel = add_derived(panel)

    coverage_report(panel)

    # Canonical column order
    ordered = [
        "fips_state", "state_name", "state_abbr", "year",
        "median_home_value", "median_gross_rent", "homeownership_rate", "vacancy_rate",
        "hpi_at_annual", "permits_total_units", "permits_1unit",
        "median_household_income", "poverty_rate",
        "population", "domestic_migration",
        "unemployment_rate",
        "mortgage_rate_30yr",
        "affordability_ratio", "rent_burden", "permits_per_1000_pop",
    ]
    panel = panel[ordered]

    # Save parquet
    out_parquet = DATA / "panel.parquet"
    panel.to_parquet(out_parquet, index=False)
    print(f"\nSaved {len(panel)} rows × {len(panel.columns)} cols -> {out_parquet}")

    # Save DuckDB
    out_db = DATA / "panel.duckdb"
    out_db.unlink(missing_ok=True)
    con = duckdb.connect(str(out_db))
    con.execute("CREATE TABLE panel AS SELECT * FROM panel")
    con.close()
    print(f"Saved DuckDB -> {out_db}")

    print("\nSample (California):")
    print(panel[panel["state_abbr"] == "CA"][
        ["year", "median_home_value", "median_household_income", "affordability_ratio",
         "unemployment_rate", "permits_per_1000_pop"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
