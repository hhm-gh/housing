"""
Collect Census Building Permits Survey (BPS) annual state-level data, 2010-2024.
Outputs: data/bps_permits.parquet

Source: Census BPS state YTD files (December = full-year total)
  https://www2.census.gov/econ/bps/State/st{YY}12y.txt

File layout (CSV, 2 header rows + 1 blank row):
  col 0  survey date (YYYYMM)
  col 1  state FIPS (integer, e.g. 1 for Alabama)
  col 4  state name
  col 6  1-unit units permitted
  col 9  2-unit units permitted
  col 12 3-4 unit units permitted
  col 15 5+ unit units permitted

Usage:
  uv run collect_census_bps.py
"""

import sys
import io
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

BASE_URL = "https://www2.census.gov/econ/bps/State/st{yy:02d}12y.txt"

STATE_FIPS = {
    "01","02","04","05","06","08","09","10","11","12",
    "13","15","16","17","18","19","20","21","22","23",
    "24","25","26","27","28","29","30","31","32","33",
    "34","35","36","37","38","39","40","41","42","44",
    "45","46","47","48","49","50","51","53","54","55","56",
}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_year(year: int, session: requests.Session) -> pd.DataFrame | None:
    url = BASE_URL.format(yy=year % 100)
    resp = session.get(url, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    # Two header rows + one blank row before data
    df = pd.read_csv(
        io.StringIO(resp.text),
        skiprows=3,
        header=None,
        dtype=str,
    )

    # Keep state rows only (FIPS col is an integer in range 01-56)
    df[1] = df[1].str.strip().str.zfill(2)
    df = df[df[1].isin(STATE_FIPS)].copy()

    # Numeric unit columns
    for col in [6, 9, 12, 15]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    result = pd.DataFrame({
        "fips_state": df[1].values,
        "state_name": df[4].str.strip().values,
        "year": year,
        "permits_total_units": (df[6] + df[9] + df[12] + df[15]).values,
        "permits_1unit": df[6].values,
    })
    return result


def main():
    Path("data").mkdir(exist_ok=True)
    session = _session()

    frames = []
    for year in range(2010, 2025):
        print(f"  {year}...", end=" ", flush=True)
        df = fetch_year(year, session)
        if df is not None and not df.empty:
            frames.append(df)
            print(f"ok ({len(df)} states)")
        else:
            print("skipped (file not found)")
        time.sleep(0.2)

    if not frames:
        print("ERROR: no data collected")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["fips_state", "year"]).reset_index(drop=True)

    out = Path("data/bps_permits.parquet")
    combined.to_parquet(out, index=False)
    print(f"\nSaved {len(combined)} rows -> {out}")
    print(combined.dtypes)
    print(combined.head())


if __name__ == "__main__":
    main()
