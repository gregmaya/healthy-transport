"""
Add Frederiksberg DAR entrance points to the Nørrebro DAR GeoPackage.

Frederiksberg is municipality 0147. The original download_bbr_dar.py only
fetched Copenhagen (0101), so the buffer zone on the Frederiksberg side has
no entrance points, leaving score_health_* artificially low on that edge.

This script:
  1. Downloads Adressepunkt for municipality 0147 from Datafordeleren
  2. Filters to TD/TK origin types (accurate door/facade points only)
  3. Clips to the 1,000m scoring buffer around the Nørrebro boundary
  4. Appends new points to data/raw/dar/norrebro_dar_adressepunkt.gpkg

After running this script, re-run the following in order:
    python scripts/process/process_buildings.py
    python scripts/integrate/integrate_buildings.py
    python scripts/integrate/integrate_population_typology.py
    python scripts/score/score_bus_routes.py
    python scripts/export/export_bus_route_segments.py
    python3 scripts/web/generate_scatter_svg.py

Credentials: DATAFORDELEREN_USERNAME / DATAFORDELEREN_PASSWORD in .env

Usage:
    python scripts/process/add_frederiksberg_dar.py
"""

import gzip
import json
import logging
import os
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    CRS_DENMARK,
    DAR_ADRESSEPUNKT_OUTPUT,
    DAR_ENTITIES,
    DAR_RAW_DIR,
    DATAFORDELER_FILE_DOWNLOAD_URL,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    SCORING_BUFFER_M,
)

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

FREDERIKSBERG_CODE = "0147"

VALID_ORIGINS = {"TD", "TK"}  # door (TD) and facade (TK) — same filter as Copenhagen


def download_adressepunkt(output_path: Path) -> Path:
    if output_path.exists():
        log.info("Using cached file: %s", output_path.name)
        return output_path

    username = os.getenv("DATAFORDELEREN_USERNAME")
    password = os.getenv("DATAFORDELEREN_PASSWORD")
    if not username or not password:
        raise ValueError(
            "Credentials not found. Set DATAFORDELEREN_USERNAME and "
            "DATAFORDELEREN_PASSWORD in .env"
        )

    params = {
        "username": username,
        "password": password,
        "Register": "DAR",
        "LatestTotalForEntity": DAR_ENTITIES["adressepunkt"],
        "Type": "Current",
        "Format": "JSON",
        "MunicipalityCode": FREDERIKSBERG_CODE,
    }

    log.info("Downloading Adressepunkt for municipality %s ...", FREDERIKSBERG_CODE)
    r = requests.get(DATAFORDELER_FILE_DOWNLOAD_URL, params=params, stream=True, timeout=600)
    r.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    log.info("Downloaded: %.1f MB → %s", output_path.stat().st_size / 1e6, output_path.name)
    return output_path


def parse_archive(filepath: Path) -> list[dict]:
    with open(filepath, "rb") as f:
        magic = f.read(2)

    if magic == b"PK":
        with zipfile.ZipFile(filepath, "r") as z:
            json_files = [n for n in z.namelist() if n.endswith(".json")]
            log.info("ZIP contains: %s", json_files[0] if json_files else "(none)")
            with z.open(json_files[0]) as f:
                records = json.load(f)
    else:
        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            records = json.load(f)

    log.info("Parsed %d records", len(records))
    return records


def to_geodataframe(records: list[dict]) -> gpd.GeoDataFrame:
    rows = []
    for rec in records:
        pos = rec.get("position")
        if isinstance(pos, str) and pos.startswith("POINT"):
            coords = pos.replace("POINT", "").strip().strip("()")
            parts = coords.split()
            if len(parts) == 2:
                rec["_x"], rec["_y"] = float(parts[0]), float(parts[1])
                rows.append(rec)

    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(r["_x"], r["_y"]) for r in rows],
        crs=CRS_DENMARK,
    )
    return gdf.drop(columns=["_x", "_y"], errors="ignore")


def main() -> None:
    # Load boundary
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    buffer_geom = boundary.to_crs(CRS_DENMARK).geometry.union_all().buffer(SCORING_BUFFER_M)
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_geom], crs=CRS_DENMARK)

    # Download
    zip_path = DAR_RAW_DIR / f"adressepunkt_{FREDERIKSBERG_CODE}.zip"
    zip_path = download_adressepunkt(zip_path)

    # Parse and build GeoDataFrame
    records = parse_archive(zip_path)
    gdf = to_geodataframe(records)
    log.info("All Frederiksberg Adressepunkt: %d features", len(gdf))

    # Filter to accurate entrance types
    if "oprindelse_tekniskStandard" in gdf.columns:
        gdf = gdf[gdf["oprindelse_tekniskStandard"].isin(VALID_ORIGINS)]
        log.info("After TD/TK filter: %d features", len(gdf))

    # Clip to scoring buffer
    gdf_clip = gpd.sjoin(gdf, buffer_gdf[["geometry"]], how="inner", predicate="within")
    gdf_clip = gdf_clip[[c for c in gdf.columns if c in gdf_clip.columns]]
    log.info(
        "After clip to %dm buffer: %d features",
        SCORING_BUFFER_M, len(gdf_clip),
    )

    if gdf_clip.empty:
        log.error("No Frederiksberg points fell within the scoring buffer — check CRS or boundary.")
        sys.exit(1)

    # Load existing GPkg to align columns
    existing = gpd.read_file(DAR_ADRESSEPUNKT_OUTPUT)
    log.info("Existing norrebro_dar_adressepunkt.gpkg: %d features", len(existing))

    # Check for already-added Frederiksberg points (idempotency)
    if "kommunekode" in existing.columns:
        already = existing[existing["kommunekode"] == FREDERIKSBERG_CODE]
        if len(already) > 0:
            log.info(
                "Frederiksberg (%s) already present: %d features — skipping.",
                FREDERIKSBERG_CODE, len(already),
            )
            return

    # Align columns: keep only columns present in the existing file
    shared_cols = [c for c in existing.columns if c in gdf_clip.columns and c != "geometry"]
    gdf_clip = gdf_clip[shared_cols + ["geometry"]]

    combined = pd.concat([existing, gdf_clip], ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=existing.crs)

    combined.to_file(DAR_ADRESSEPUNKT_OUTPUT, driver="GPKG")
    log.info(
        "Saved %d features (%d new Frederiksberg) → %s",
        len(combined), len(gdf_clip), DAR_ADRESSEPUNKT_OUTPUT,
    )
    log.info("Next: re-run process_buildings.py → integrate_buildings.py → integrate_population_typology.py")


if __name__ == "__main__":
    main()
