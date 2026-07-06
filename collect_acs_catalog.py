"""
Fetch an ACS variable catalog from the Census API and save locally.
No API key required.

Outputs: data/acs_variables_{survey}_{year}.parquet
  Columns: name, label, concept, group, predicate_type, survey, year

Usage:
  uv run collect_acs_catalog.py                        # ACS 1-year 2023
  uv run collect_acs_catalog.py 2022                   # ACS 1-year 2022
  uv run collect_acs_catalog.py 2023 --survey acs5     # ACS 5-year 2023
  uv run collect_acs_catalog.py 2022 --survey acs5     # ACS 5-year 2022
"""

import argparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

CATALOG_URL = "https://api.census.gov/data/{year}/acs/{survey}/variables.json"

# Variables that are geography/filter predicates, not data fields
_SKIP = {"for", "in", "ucgid", "NAME"}


def fetch_catalog(year: int, survey: str) -> pd.DataFrame:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))

    url = CATALOG_URL.format(year=year, survey=survey)
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    variables = resp.json()["variables"]

    rows = []
    for name, meta in variables.items():
        if name in _SKIP:
            continue
        if meta.get("predicateOnly"):
            continue
        rows.append({
            "name":           name,
            "label":          meta.get("label", ""),
            "concept":        meta.get("concept", ""),
            "group":          meta.get("group", ""),
            "predicate_type": meta.get("predicateType", ""),
            "survey":         survey,
            "year":           year,
        })

    df = pd.DataFrame(rows).sort_values(["group", "name"]).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="Fetch ACS variable catalog from Census API.")
    parser.add_argument("year", nargs="?", type=int, default=2023,
                        help="ACS vintage year (default: 2023)")
    parser.add_argument("--survey", choices=["acs1", "acs5"], default="acs1",
                        help="ACS survey type: acs1 (1-year) or acs5 (5-year) (default: acs1)")
    args = parser.parse_args()

    label = "1-year" if args.survey == "acs1" else "5-year"
    print(f"Fetching ACS {label} {args.year} variable catalog...")
    df = fetch_catalog(args.year, args.survey)

    Path("data").mkdir(exist_ok=True)
    out = Path(f"data/acs_variables_{args.survey}_{args.year}.parquet")
    df.to_parquet(out, index=False)

    print(f"Saved {len(df):,} variables → {out}")
    print(f"  Concept groups : {df['concept'].nunique():,}")
    print(f"  Table groups   : {df['group'].nunique():,}")
    print(f"\nSample:")
    print(df[["name", "concept", "label"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
