"""
Fetch the ACS 1-year variable catalog from the Census API and save locally.
No API key required.

Outputs: data/acs_variables.parquet
  Columns: name, label, concept, group, predicate_type, year

Usage:
  uv run collect_acs_catalog.py            # defaults to 2023
  uv run collect_acs_catalog.py 2022       # specific year
"""

import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path

CATALOG_URL = "https://api.census.gov/data/{year}/acs/acs1/variables.json"

# Variables that are geography/filter predicates, not data fields
_SKIP = {"for", "in", "ucgid", "NAME"}


def fetch_catalog(year: int) -> pd.DataFrame:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))

    resp = session.get(CATALOG_URL.format(year=year), timeout=60)
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
            "year":           year,
        })

    df = pd.DataFrame(rows).sort_values(["group", "name"]).reset_index(drop=True)
    return df


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023

    print(f"Fetching ACS 1-year variable catalog for {year}...")
    df = fetch_catalog(year)

    Path("data").mkdir(exist_ok=True)
    out = Path("data/acs_variables.parquet")
    df.to_parquet(out, index=False)

    print(f"Saved {len(df):,} variables → {out}")
    print(f"  Concept groups : {df['concept'].nunique():,}")
    print(f"  Table groups   : {df['group'].nunique():,}")
    print(f"\nSample:")
    print(df[["name", "concept", "label"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
