"""
Collect 30-year fixed mortgage rate (Freddie Mac PMMS) from FRED, 2010-2024.
Outputs: data/fred_mortgage.parquet

Series: MORTGAGE30US (weekly, not seasonally adjusted)
Aggregation: annual mean of weekly observations.

Usage:
  FRED_API_KEY=<your_key> uv run collect_fred.py

Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
"""

import os
import sys
import pandas as pd
from fredapi import Fred
from pathlib import Path


def main():
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        print("Error: set FRED_API_KEY environment variable")
        print("Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html")
        sys.exit(1)

    Path("data").mkdir(exist_ok=True)
    fred = Fred(api_key=api_key)

    print("Fetching MORTGAGE30US from FRED...", end=" ", flush=True)
    series = fred.get_series("MORTGAGE30US", observation_start="2010-01-01", observation_end="2024-12-31")
    print("ok")

    annual = (
        series
        .dropna()
        .resample("YE")
        .mean()
        .reset_index()
    )
    annual.columns = ["date", "mortgage_rate_30yr"]
    annual["year"] = annual["date"].dt.year
    annual = annual[["year", "mortgage_rate_30yr"]]

    out = Path("data/fred_mortgage.parquet")
    annual.to_parquet(out, index=False)
    print(f"Saved {len(annual)} rows -> {out}")
    print(annual)


if __name__ == "__main__":
    main()
