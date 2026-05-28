"""
Collect BLS LAUS state-level unemployment rates, 2010-2024.
Outputs: data/bls_laus.parquet

Series pattern: LASST{fips}0000000000003  (not seasonally adjusted, unemployment rate)

BLS API v2 limits without a key: 25 series/request, 10 years/request.
This script batches accordingly. Set BLS_API_KEY for the 50-series / 20-year tier.

Usage:
  uv run collect_bls.py
  BLS_API_KEY=<your_key> uv run collect_bls.py
"""

import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# 2-digit state FIPS codes for all 50 states + DC
STATE_FIPS = [
    "01","02","04","05","06","08","09","10","11","12",
    "13","15","16","17","18","19","20","21","22","23",
    "24","25","26","27","28","29","30","31","32","33",
    "34","35","36","37","38","39","40","41","42","44",
    "45","46","47","48","49","50","51","53","54","55","56",
]

FIPS_TO_NAME = {
    "01":"Alabama","02":"Alaska","04":"Arizona","05":"Arkansas","06":"California",
    "08":"Colorado","09":"Connecticut","10":"Delaware","11":"District of Columbia","12":"Florida",
    "13":"Georgia","15":"Hawaii","16":"Idaho","17":"Illinois","18":"Indiana",
    "19":"Iowa","20":"Kansas","21":"Kentucky","22":"Louisiana","23":"Maine",
    "24":"Maryland","25":"Massachusetts","26":"Michigan","27":"Minnesota","28":"Mississippi",
    "29":"Missouri","30":"Montana","31":"Nebraska","32":"Nevada","33":"New Hampshire",
    "34":"New Jersey","35":"New Mexico","36":"New York","37":"North Carolina","38":"North Dakota",
    "39":"Ohio","40":"Oklahoma","41":"Oregon","42":"Pennsylvania","44":"Rhode Island",
    "45":"South Carolina","46":"South Dakota","47":"Tennessee","48":"Texas","49":"Utah",
    "50":"Vermont","51":"Virginia","53":"Washington","54":"West Virginia","55":"Wisconsin",
    "56":"Wyoming",
}


def series_id(fips: str) -> str:
    return f"LASST{fips}0000000000003"


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_batch(
    series_ids: list[str],
    start_year: int,
    end_year: int,
    api_key: str,
    session: requests.Session,
) -> list[dict]:
    payload: dict = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    resp = session.post(
        BLS_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") != "REQUEST_SUCCEEDED":
        msg = result.get("message", result.get("status"))
        raise RuntimeError(f"BLS API error: {msg}")

    return result["Results"]["series"]


def parse_series(series_list: list[dict]) -> pd.DataFrame:
    rows = []
    for s in series_list:
        fips = s["seriesID"][5:7]  # chars 5-6 of LASST{fips}...
        for obs in s["data"]:
            period = obs["period"]
            # M13 = annual average (use if present); M01-M12 = monthly (average later)
            if period == "M13" or (period.startswith("M") and period != "M13"):
                try:
                    rows.append({
                        "fips_state": fips,
                        "year": int(obs["year"]),
                        "period": period,
                        "value": float(obs["value"]),
                    })
                except ValueError:
                    pass

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Prefer M13 annual averages; fall back to mean of monthly
    annual_rows = df[df["period"] == "M13"][["fips_state", "year", "value"]].copy()
    monthly = df[df["period"] != "M13"]
    monthly_avg = monthly.groupby(["fips_state", "year"])["value"].mean().reset_index()

    # Use M13 where available, monthly average elsewhere
    combined = pd.concat([annual_rows, monthly_avg[~monthly_avg.set_index(["fips_state","year"]).index.isin(
        annual_rows.set_index(["fips_state","year"]).index
    )]])
    return combined.rename(columns={"value": "unemployment_rate"})[["fips_state", "year", "unemployment_rate"]]


def main():
    api_key = os.environ.get("BLS_API_KEY", "")
    max_series = 50 if api_key else 25
    max_years = 20 if api_key else 10

    Path("data").mkdir(exist_ok=True)
    session = _session()

    all_series = [series_id(f) for f in STATE_FIPS]
    # Split states into batches of max_series
    state_batches = [all_series[i:i+max_series] for i in range(0, len(all_series), max_series)]

    # Split time range into 10-year (or 20-year) chunks
    years = list(range(2010, 2025))
    time_batches = [years[i:i+max_years] for i in range(0, len(years), max_years)]
    time_ranges = [(b[0], b[-1]) for b in time_batches]

    frames = []
    total = len(state_batches) * len(time_ranges)
    done = 0
    for s_batch in state_batches:
        for start, end in time_ranges:
            done += 1
            fips_range = f"{s_batch[0][5:7]}-{s_batch[-1][5:7]}"
            print(f"  [{done}/{total}] states {fips_range}, {start}-{end}...", end=" ", flush=True)
            series_list = fetch_batch(s_batch, start, end, api_key, session)
            df = parse_series(series_list)
            frames.append(df)
            print(f"ok ({len(df)} rows)")
            time.sleep(0.5)

    combined = pd.concat(frames, ignore_index=True)

    # If M13 annual averages were present, we already have one row per state/year.
    # Deduplicate in case of overlapping time range batches.
    combined = combined.drop_duplicates(["fips_state", "year"])

    combined["state_name"] = combined["fips_state"].map(FIPS_TO_NAME)
    combined = combined[["fips_state", "state_name", "year", "unemployment_rate"]]
    combined = combined.sort_values(["fips_state", "year"]).reset_index(drop=True)

    out = Path("data/bls_laus.parquet")
    combined.to_parquet(out, index=False)
    print(f"\nSaved {len(combined)} rows -> {out}")
    print(combined.dtypes)
    print(combined.head())


if __name__ == "__main__":
    main()
