"""
Collect Census Population Estimates (PEP) for all states, 2010-2024.
Outputs: data/pep_population.parquet

Two-vintage approach:
  2010-2019  Census PEP API, 2019 vintage
  2020-2024  NST-EST2024 flat file download

Variables: total population, net domestic migration

Usage:
  CENSUS_API_KEY=<your_key> uv run collect_census_pep.py
"""

import os
import sys
import re
import io
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

PEP_2019_URL = "https://api.census.gov/data/2019/pep/population"

# Census publishes annual NST-EST files; try 2024 then 2023 as fallback
NST_URLS = [
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv",
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/state/totals/NST-EST2023-ALLDATA.csv",
]


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


# ── 2010-2019 via PEP API ─────────────────────────────────────────────────────

def fetch_2010_2019(api_key: str, session: requests.Session) -> pd.DataFrame:
    params = {
        "get": "NAME,POP,DATE_CODE,DATE_DESC",
        "for": "state:*",
        "key": api_key,
    }
    resp = session.get(PEP_2019_URL, params=params, timeout=60)
    resp.raise_for_status()
    header, *rows = resp.json()
    df = pd.DataFrame(rows, columns=header)

    # DATE_DESC is like "7/1/2015 population estimate" or "4/1/2010 Census population"
    # Keep only July 1 annual estimates; skip the April 2010 census and estimates base rows
    df = df[df["DATE_DESC"].str.startswith("7/1/")]
    df["year"] = df["DATE_DESC"].str.extract(r"7/1/(\d{4})").astype(int)

    df = df.rename(columns={"state": "fips_state", "NAME": "state_name", "POP": "population"})
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df["domestic_migration"] = None  # not available in this vintage

    return df[["fips_state", "state_name", "year", "population", "domestic_migration"]]


# ── 2020-2024 via NST-EST flat file ──────────────────────────────────────────

def fetch_2020_2024(session: requests.Session) -> pd.DataFrame:
    raw = None
    for url in NST_URLS:
        resp = session.get(url, timeout=60)
        if resp.status_code == 200:
            raw = resp
            break

    if raw is None:
        raise RuntimeError("Could not download NST-EST population file from Census")

    df = pd.read_csv(io.StringIO(raw.text))

    # Filter to state rows only (SUMLEV 040)
    df = df[df["SUMLEV"] == 40].copy()

    # FIPS is in STATE column (integer); zero-pad to 2 digits
    df["fips_state"] = df["STATE"].astype(str).str.zfill(2)

    # Detect available POPESTIMATE years in the file
    pop_cols = [c for c in df.columns if re.match(r"POPESTIMATE20[2-9]\d$", c)]
    mig_cols = [c for c in df.columns if re.match(r"DOMESTICMIG20[2-9]\d$", c)]

    frames = []
    for col in pop_cols:
        year = int(col[-4:])
        row = df[["fips_state", "NAME", col]].copy()
        row = row.rename(columns={"NAME": "state_name", col: "population"})
        row["year"] = year

        mig_col = f"DOMESTICMIG{year}"
        row["domestic_migration"] = df[mig_col].values if mig_col in df.columns else None

        frames.append(row)

    return pd.concat(frames, ignore_index=True)[
        ["fips_state", "state_name", "year", "population", "domestic_migration"]
    ]


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        print("Error: set CENSUS_API_KEY environment variable")
        sys.exit(1)

    Path("data").mkdir(exist_ok=True)
    session = _session()

    print("Fetching 2010-2019 (PEP API 2019 vintage)...", end=" ", flush=True)
    df_hist = fetch_2010_2019(api_key, session)
    print(f"ok — {len(df_hist)} rows")

    print("Fetching 2020-2024 (NST-EST flat file)...", end=" ", flush=True)
    df_recent = fetch_2020_2024(session)
    print(f"ok — {len(df_recent)} rows")

    combined = pd.concat([df_hist, df_recent], ignore_index=True)
    combined["population"] = pd.to_numeric(combined["population"], errors="coerce")
    combined["domestic_migration"] = pd.to_numeric(combined["domestic_migration"], errors="coerce")
    combined = combined.sort_values(["fips_state", "year"]).reset_index(drop=True)

    # Filter to 2010-2024 only
    combined = combined[combined["year"].between(2010, 2024)]

    out = Path("data/pep_population.parquet")
    combined.to_parquet(out, index=False)
    print(f"\nSaved {len(combined)} rows -> {out}")
    print(combined.dtypes)
    print(combined.head())


if __name__ == "__main__":
    main()
