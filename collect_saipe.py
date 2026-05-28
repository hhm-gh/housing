"""
Collect SAIPE (Small Area Income and Poverty Estimates) for all states, 2010-2024.
Outputs: data/saipe.parquet

Variables:
  SAEMHI_PT       median household income estimate
  SAEPOVRTALL_PT  all-ages poverty rate estimate (0-100)

SAIPE is annual; 2024 data was released January 2026.

Usage:
  CENSUS_API_KEY=<your_key> uv run collect_saipe.py
"""

import os
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

BASE_URL = "https://api.census.gov/data/timeseries/poverty/saipe"

VARIABLES = ["NAME", "SAEMHI_PT", "SAEPOVRTALL_PT"]


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_all_years(api_key: str, session: requests.Session) -> pd.DataFrame:
    params = {
        "get": ",".join(VARIABLES),
        "for": "state:*",
        "time": "from 2010 to 2024",
        "key": api_key,
    }
    resp = session.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    header, *rows = data
    return pd.DataFrame(rows, columns=header)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "state": "fips_state",
        "NAME": "state_name",
        "time": "year",
        "SAEMHI_PT": "median_household_income",
        "SAEPOVRTALL_PT": "poverty_rate",
    })

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["median_household_income"] = pd.to_numeric(df["median_household_income"], errors="coerce")
    df["poverty_rate"] = pd.to_numeric(df["poverty_rate"], errors="coerce")

    for col in ["median_household_income", "poverty_rate"]:
        df.loc[df[col] < 0, col] = None

    return df[["fips_state", "state_name", "year", "median_household_income", "poverty_rate"]]


def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        print("Error: set CENSUS_API_KEY environment variable")
        sys.exit(1)

    Path("data").mkdir(exist_ok=True)
    session = _session()

    print("Fetching SAIPE 2010-2024 (single request)...", end=" ", flush=True)
    try:
        df = fetch_all_years(api_key, session)
        print("ok")
    except requests.HTTPError as e:
        print(f"HTTP {e.response.status_code}")
        sys.exit(1)

    df = clean(df)
    df = df.sort_values(["fips_state", "year"]).reset_index(drop=True)

    out = Path("data/saipe.parquet")
    df.to_parquet(out, index=False)
    print(f"Saved {len(df)} rows -> {out}")
    print(df.dtypes)
    print(df.head())


if __name__ == "__main__":
    main()
