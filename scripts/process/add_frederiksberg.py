"""
Add Frederiksberg to the sub-district boundary and population files.

Frederiksberg is a separate municipality (code 147) entirely surrounded by
Copenhagen. It has no internal sub-districts in KKBEF8 (which only covers
Copenhagen municipality). This script:

  1. Downloads the Frederiksberg boundary polygon from the Copenhagen Municipality
     WFS (layer: kommunegr_frberg) and appends it to
     data/raw/demographics/copenhagen_kvartergrænser.gpkg as a single feature
     with kvarternr=147, kvarternavn="Frederiksberg".

  2. Fetches Frederiksberg population by single year of age from Statistics Denmark
     FOLK1A (municipality 147, 2025Q4), aggregates into the same 5-year bands
     used by KKBEF8, and appends those rows to
     data/processed/all_districts_population.csv.

After running this script, both files are complete for Phase B integration.

Usage:
    python scripts/process/add_frederiksberg.py
"""

import io
import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

KVARTERGRAENSER_GPKG = PROJECT_ROOT / "data" / "raw" / "demographics" / "copenhagen_kvartergrænser.gpkg"
POPULATION_CSV       = PROJECT_ROOT / "data" / "processed" / "all_districts_population.csv"

FREDERIKSBERG_GM_ID  = 147
FREDERIKSBERG_NAME   = "Frederiksberg"
PERIOD               = "2025Q4"

# 5-year age bands matching the KKBEF8 convention
AGE_BANDS = [
    ("0-4 years",   range(0,   5)),
    ("5-9 years",   range(5,  10)),
    ("10-14 years", range(10, 15)),
    ("15-19 years", range(15, 20)),
    ("20-24 years", range(20, 25)),
    ("25-29 years", range(25, 30)),
    ("30-34 years", range(30, 35)),
    ("35-39 years", range(35, 40)),
    ("40-44 years", range(40, 45)),
    ("45-49 years", range(45, 50)),
    ("50-54 years", range(50, 55)),
    ("55-59 years", range(55, 60)),
    ("60-64 years", range(60, 65)),
    ("65-69 years", range(65, 70)),
    ("70-74 years", range(70, 75)),
    ("75-79 years", range(75, 80)),
    ("80-84 years", range(80, 85)),
    ("85-89 years", range(85, 90)),
    ("90-94 years", range(90, 95)),
    ("95+ years",   range(95, 100)),  # FOLK1A goes to 99 by single year; 95-99 as proxy
]


def fetch_boundary() -> gpd.GeoDataFrame:
    log.info("Fetching Frederiksberg boundary from KK WFS ...")
    url = (
        "https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0"
        "&request=GetFeature&typeName=k101:kommunegr_frberg"
        "&outputFormat=json&SRSNAME=EPSG:25832"
    )
    gdf = gpd.read_file(url)
    area_km2 = gdf.geometry.area.sum() / 1e6
    log.info("  %d polygon(s), area %.2f km²", len(gdf), area_km2)
    # Dissolve to a single polygon and standardise columns
    gdf_out = gpd.GeoDataFrame(
        {
            "kvarternr":   [FREDERIKSBERG_GM_ID],
            "kvarternavn": [FREDERIKSBERG_NAME],
        },
        geometry=[gdf.geometry.union_all()],
        crs=gdf.crs,
    )
    return gdf_out


def fetch_population() -> pd.DataFrame:
    log.info("Fetching Frederiksberg population from StatBank FOLK1A (municipality 147) ...")
    ages = [str(i) for i in range(100)]  # 0–99 single years
    payload = {
        "table": "FOLK1A",
        "format": "CSV",
        "lang": "en",
        "variables": [
            {"code": "OMRÅDE", "values": ["147"]},
            {"code": "KØN",    "values": ["TOT"]},
            {"code": "ALDER",  "values": ages},
            {"code": "Tid",    "values": ["2025K4"]},
        ],
    }
    r = requests.post("https://api.statbank.dk/v1/data", json=payload, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep=";")
    # Parse age as integer
    df["age_int"] = df["ALDER"].str.extract(r"(\d+)").astype(int)
    total = df["INDHOLD"].sum()
    log.info("  Fetched %d age rows, total population %d", len(df), total)

    rows = []
    for band_label, age_range in AGE_BANDS:
        count = df[df["age_int"].isin(age_range)]["INDHOLD"].sum()
        rows.append({
            "gm_id":       FREDERIKSBERG_GM_ID,
            "period":      PERIOD,
            "ages":        band_label,
            "kvarternavn": FREDERIKSBERG_NAME,
            "people":      int(count),
        })

    df_out = pd.DataFrame(rows)
    log.info("  Aggregated into %d age bands, total %d", len(df_out), df_out["people"].sum())
    return df_out


def update_boundary(new_feature: gpd.GeoDataFrame) -> None:
    log.info("Loading existing boundary file: %s", KVARTERGRAENSER_GPKG)
    existing = gpd.read_file(KVARTERGRAENSER_GPKG)

    if FREDERIKSBERG_GM_ID in existing["kvarternr"].values:
        log.info("  Frederiksberg (147) already present — skipping boundary update.")
        return

    log.info("  Appending Frederiksberg polygon (%d → %d features) ...",
             len(existing), len(existing) + 1)
    # Align columns — use only shared columns, fill missing with None
    combined = pd.concat([existing, new_feature], ignore_index=True)
    combined = gpd.GeoDataFrame(combined, crs=existing.crs)
    combined.to_file(KVARTERGRAENSER_GPKG, driver="GPKG")
    log.info("  Saved → %s", KVARTERGRAENSER_GPKG)


def update_population(new_rows: pd.DataFrame) -> None:
    log.info("Loading existing population CSV: %s", POPULATION_CSV)
    existing = pd.read_csv(POPULATION_CSV)

    if FREDERIKSBERG_GM_ID in existing["gm_id"].values:
        log.info("  Frederiksberg (147) already present — skipping population update.")
        return

    log.info("  Appending %d Frederiksberg rows (%d → %d total) ...",
             len(new_rows), len(existing), len(existing) + len(new_rows))
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined = combined.sort_values(["gm_id", "ages"])
    combined.to_csv(POPULATION_CSV, index=False)
    log.info("  Saved → %s (%.1f KB)", POPULATION_CSV, POPULATION_CSV.stat().st_size / 1024)


def main() -> None:
    boundary_feature = fetch_boundary()
    population_rows  = fetch_population()

    update_boundary(boundary_feature)
    update_population(population_rows)

    log.info("Done. Frederiksberg (gm_id=147) added to both files.")
    log.info("Next: re-run integrate_population_typology.py → score_bus_routes.py → export.")


if __name__ == "__main__":
    main()
