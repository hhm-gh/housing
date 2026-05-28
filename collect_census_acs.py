"""
Collect ACS 1-year housing variables for all states, 2010-2024.
Outputs: data/acs_housing.parquet

Variables:
  B25077_001E  median home value (owner-occupied)
  B25064_001E  median gross rent
  B25003_001E  total occupied housing units  => homeownership rate
  B25003_002E  owner-occupied units
  B25002_001E  total housing units           => vacancy rate
  B25002_003E  vacant units

Usage:
  CENSUS_API_KEY=<your_key> uv run collect_census_acs.py

Get a free key at https://api.census.gov/data/key_signup.html
"""

import os
import sys
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

BASE_URL = "https://api.census.gov/data/{year}/acs/acs1"

VARIABLES = [
    "NAME",
    "B25077_001E",  # median home value
    "B25064_001E",  # median gross rent
    "B25003_001E",  # occupied units total
    "B25003_002E",  # owner-occupied units
    "B25002_001E",  # total housing units
    "B25002_003E",  # vacant units
]

# 2020 ACS 1-year was not released (COVID data quality issues)
YEARS = [y for y in range(2010, 2025) if y != 2020]


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_year(year: int, api_key: str, session: requests.Session) -> pd.DataFrame:
    params = {
        "get": ",".join(VARIABLES),
        "for": "state:*",
        "key": api_key,
    }
    resp = session.get(BASE_URL.format(year=year), params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    header, *rows = data
    df = pd.DataFrame(rows, columns=header)
    df["year"] = year
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "state": "fips_state",
        "NAME": "state_name",
        "B25077_001E": "median_home_value",
        "B25064_001E": "median_gross_rent",
        "B25003_001E": "occupied_units",
        "B25003_002E": "owner_occupied_units",
        "B25002_001E": "total_housing_units",
        "B25002_003E": "vacant_units",
    })

    numeric_cols = [
        "median_home_value", "median_gross_rent",
        "occupied_units", "owner_occupied_units",
        "total_housing_units", "vacant_units",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Negative values are Census sentinel codes meaning "not available"
    for col in numeric_cols:
        df.loc[df[col] < 0, col] = None

    df["homeownership_rate"] = df["owner_occupied_units"] / df["occupied_units"]
    df["vacancy_rate"] = df["vacant_units"] / df["total_housing_units"]

    return df[[
        "fips_state", "state_name", "year",
        "median_home_value", "median_gross_rent",
        "homeownership_rate", "vacancy_rate",
    ]]


def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        print("Error: set CENSUS_API_KEY environment variable")
        print("Get a free key at https://api.census.gov/data/key_signup.html")
        sys.exit(1)

    Path("data").mkdir(exist_ok=True)
    session = _session()

    frames = []
    for year in YEARS:
        print(f"  {year}...", end=" ", flush=True)
        try:
            df = fetch_year(year, api_key, session)
            frames.append(df)
            print("ok")
        except (requests.HTTPError, requests.ReadTimeout) as e:
            status = getattr(getattr(e, "response", None), "status_code", "timeout")
            print(f"{status} — skipping")
        time.sleep(0.3)

    combined = pd.concat(frames, ignore_index=True)
    combined = clean(combined)

    out = Path("data/acs_housing.parquet")
    combined.to_parquet(out, index=False)
    print(f"\nSaved {len(combined)} rows → {out}")
    print(combined.dtypes)
    print(combined.head())


if __name__ == "__main__":
    main()
