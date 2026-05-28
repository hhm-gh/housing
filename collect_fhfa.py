"""
Download FHFA All-Transactions House Price Index for all states, 2010-2024.
Outputs: data/fhfa_hpi.parquet

Source: FHFA quarterly flat file (no API key required)
  https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv

The file has no header. Columns: state_abbr, year, quarter, hpi_index.
We average the four quarters to produce an annual index value.

Usage:
  uv run collect_fhfa.py
"""

import sys
import io
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

HPI_URL = "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv"

# Postal abbreviation -> 2-digit FIPS (50 states + DC)
ABBR_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def main():
    Path("data").mkdir(exist_ok=True)
    session = _session()

    print("Downloading FHFA HPI state file...", end=" ", flush=True)
    resp = session.get(HPI_URL, timeout=60)
    resp.raise_for_status()
    print("ok")

    df = pd.read_csv(
        io.StringIO(resp.text),
        header=None,
        names=["state_abbr", "year", "quarter", "hpi_index"],
    )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["hpi_index"] = pd.to_numeric(df["hpi_index"], errors="coerce")
    df = df.dropna(subset=["year", "hpi_index"])
    df = df[df["year"].between(2010, 2024)]

    # Annual average across four quarters
    annual = (
        df.groupby(["state_abbr", "year"])["hpi_index"]
        .mean()
        .reset_index()
        .rename(columns={"hpi_index": "hpi_at_annual"})
    )

    annual["fips_state"] = annual["state_abbr"].map(ABBR_TO_FIPS)
    missing = annual[annual["fips_state"].isna()]["state_abbr"].unique()
    if len(missing):
        print(f"  Note: dropping {missing} — not in 50-state + DC scope")
    annual = annual.dropna(subset=["fips_state"])

    annual = annual[["fips_state", "state_abbr", "year", "hpi_at_annual"]]
    annual = annual.sort_values(["fips_state", "year"]).reset_index(drop=True)

    out = Path("data/fhfa_hpi.parquet")
    annual.to_parquet(out, index=False)
    print(f"Saved {len(annual)} rows -> {out}")
    print(annual.dtypes)
    print(annual.head())


if __name__ == "__main__":
    main()
