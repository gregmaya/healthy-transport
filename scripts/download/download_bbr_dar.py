"""
Download BBR Building Attributes & DAR Access Points for Nørrebro

Downloads:
- BBR (Bygnings- og Boligregistret): building point data with attributes
  (use, floor area, construction year, etc.) via WFS
- DAR (Danmarks Adresseregister): address/entrance point coordinates
  via File Download API

Credentials: DATAFORDELEREN_USERNAME and DATAFORDELEREN_PASSWORD in .env

Usage:
    python scripts/download_bbr_dar.py
"""

import gzip
import json
import logging
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv
from shapely.geometry import Point

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    BBR_ID_COLUMNS,
    BBR_KEY_ATTRIBUTES,
    BBR_LAYER,
    BBR_OUTPUT_FILE,
    BBR_RAW_DIR,
    COPENHAGEN_MUNICIPALITY_CODE,
    CRS_DENMARK,
    DAR_ADRESSEPUNKT_OUTPUT,
    DAR_ENTITIES,
    DAR_HUSNUMMER_OUTPUT,
    DAR_RAW_DIR,
    DATAFORDELER_FILE_DOWNLOAD_URL,
    DATAFORDELER_WFS,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BBR Download (WFS)
# ---------------------------------------------------------------------------


class DatafordelerenClient:
    """Client for Datafordeleren WFS services (BBR building data)."""

    def __init__(self):
        self.username = os.getenv("DATAFORDELEREN_USERNAME")
        self.password = os.getenv("DATAFORDELEREN_PASSWORD")
        if not self.username or not self.password:
            raise ValueError(
                "Credentials not found. Set DATAFORDELEREN_USERNAME and "
                "DATAFORDELEREN_PASSWORD in .env"
            )

    def _make_wfs_request(
        self,
        service_url: str,
        typename: str,
        bbox: tuple | None = None,
        max_features: int = 50000,
    ) -> gpd.GeoDataFrame:
        """Make a WFS GetFeature request and return a GeoDataFrame."""
        params = {
            "username": self.username,
            "password": self.password,
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": typename,
            "srsname": "urn:ogc:def:crs:EPSG::25832",
            "count": max_features,
        }
        if bbox:
            params["bbox"] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:25832"

        response = requests.get(service_url, params=params, timeout=120)
        response.raise_for_status()

        # Check for WFS error in response body
        content = response.text[:500]
        if "ExceptionReport" in content or "ServiceException" in content:
            raise RuntimeError(f"WFS error response: {content[:300]}")

        # Write GML to temp file and read with geopandas
        with tempfile.NamedTemporaryFile(suffix=".gml", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            gdf = gpd.read_file(tmp_path)
        finally:
            os.unlink(tmp_path)

        return gdf

    def download_bbr(self, boundary_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Download BBR building points within the study area boundary.

        Args:
            boundary_gdf: GeoDataFrame with the study area polygon (EPSG:25832)

        Returns:
            GeoDataFrame of BBR building points clipped to boundary
        """
        bounds = boundary_gdf.total_bounds  # (minx, miny, maxx, maxy)
        area_km2 = boundary_gdf.geometry.area.sum() / 1e6

        logger.info(
            "Fetching BBR data — bbox: X %.0f–%.0f, Y %.0f–%.0f (%.1f km²)",
            bounds[0], bounds[2], bounds[1], bounds[3], area_km2,
        )

        bbr = self._make_wfs_request(
            service_url=DATAFORDELER_WFS["bbr"],
            typename=BBR_LAYER,
            bbox=tuple(bounds),
        )

        if bbr.empty:
            logger.warning("No BBR features returned from WFS")
            return bbr

        logger.info("Retrieved %d BBR features from WFS", len(bbr))

        # Deduplicate by ID column
        initial = len(bbr)
        for col in BBR_ID_COLUMNS:
            if col in bbr.columns:
                bbr = bbr.drop_duplicates(subset=[col])
                removed = initial - len(bbr)
                if removed:
                    logger.info("Removed %d duplicates (by %s)", removed, col)
                break

        # Clip to actual boundary (not just bbox)
        if bbr.crs != boundary_gdf.crs:
            boundary_gdf = boundary_gdf.to_crs(bbr.crs)

        bbr_cols = list(bbr.columns)
        bbr = gpd.sjoin(bbr, boundary_gdf[["geometry"]], how="inner", predicate="within")
        # Keep only original BBR columns
        bbr = bbr[[c for c in bbr_cols if c in bbr.columns]]

        logger.info("After clipping to boundary: %d buildings", len(bbr))

        # Log available key attributes
        for label, col_name in BBR_KEY_ATTRIBUTES.items():
            if col_name in bbr.columns:
                non_null = bbr[col_name].notna().sum()
                logger.info("  %s (%s): %d/%d non-null", label, col_name, non_null, len(bbr))
            else:
                logger.warning("  %s (%s): column NOT found", label, col_name)

        return bbr


# ---------------------------------------------------------------------------
# DAR Download (File Download API)
# ---------------------------------------------------------------------------


class DARDownloader:
    """Client for DAR data via Datafordeler File Download API."""

    def __init__(self):
        self.username = os.getenv("DATAFORDELEREN_USERNAME")
        self.password = os.getenv("DATAFORDELEREN_PASSWORD")
        if not self.username or not self.password:
            raise ValueError(
                "Credentials not found. Set DATAFORDELEREN_USERNAME and "
                "DATAFORDELEREN_PASSWORD in .env"
            )

    def _download_file(
        self,
        entity: str,
        municipality_code: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """Download a DAR entity file from the File Download API."""
        params = {
            "username": self.username,
            "password": self.password,
            "Register": "DAR",
            "LatestTotalForEntity": entity,
            "Type": "Current",
            "Format": "JSON",
        }
        if municipality_code:
            params["MunicipalityCode"] = municipality_code

        if output_path is None:
            suffix = f"_{municipality_code}" if municipality_code else "_national"
            output_path = DAR_RAW_DIR / f"{entity.lower()}{suffix}.zip"

        # Use cached file if it exists
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info("Using cached %s (%.1f MB): %s", entity, size_mb, output_path.name)
            return output_path

        logger.info("Downloading %s (municipality %s)...", entity, municipality_code or "national")

        response = requests.get(
            DATAFORDELER_FILE_DOWNLOAD_URL,
            params=params,
            stream=True,
            timeout=600,
        )
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and downloaded % (1024 * 1024) < 8192:
                        pct = downloaded / total_size * 100
                        logger.info("  %.0f%% (%d MB)", pct, downloaded // (1024 * 1024))

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info("Downloaded %s: %.1f MB → %s", entity, size_mb, output_path.name)
        return output_path

    def download_adressepunkt(self, municipality_code: str) -> Path:
        """Download Adressepunkt for a municipality."""
        return self._download_file(DAR_ENTITIES["adressepunkt"], municipality_code)

    def download_husnummer(self, municipality_code: str | None = None) -> Path:
        """Download Husnummer (national only — not available per municipality)."""
        if municipality_code:
            logger.info("Husnummer not available per municipality, downloading national file...")
        return self._download_file(DAR_ENTITIES["husnummer"])


def parse_dar_archive(filepath: Path) -> list[dict]:
    """Parse a DAR JSON archive (ZIP or gzip) into a list of records."""
    logger.info("Parsing %s...", filepath.name)

    # Detect format by reading magic bytes
    with open(filepath, "rb") as f:
        magic = f.read(2)

    if magic == b"PK":
        # ZIP file
        with zipfile.ZipFile(filepath, "r") as z:
            json_files = [n for n in z.namelist() if n.endswith(".json")]
            if not json_files:
                raise ValueError(f"No JSON files found in {filepath.name}")
            logger.info("  ZIP contains: %s", json_files[0])
            with z.open(json_files[0]) as f:
                records = json.load(f)
        logger.info("  Parsed %d records from ZIP", len(records))
        return records
    else:
        # Try gzip
        try:
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                records = json.load(f)
            logger.info("  Parsed %d records from gzip", len(records))
            return records
        except (gzip.BadGzipFile, json.JSONDecodeError) as e:
            raise ValueError(f"Cannot parse {filepath.name}: not ZIP or valid gzip ({e})")


def adressepunkt_to_geodataframe(records: list[dict]) -> gpd.GeoDataFrame:
    """Convert DAR Adressepunkt records to a GeoDataFrame with Point geometries."""
    rows = []
    for rec in records:
        x = y = None

        # Parse position field — WKT format "POINT (x y)" or "POINT(x y)"
        pos = rec.get("position")
        if isinstance(pos, str) and pos.startswith("POINT"):
            # Strip "POINT", parentheses, and extra whitespace
            coords_str = pos.replace("POINT", "").strip().strip("()")
            parts = coords_str.split()
            if len(parts) == 2:
                x, y = float(parts[0]), float(parts[1])

        if x is not None and y is not None:
            rec["_x"] = float(x)
            rec["_y"] = float(y)
            rows.append(rec)

    if not rows:
        logger.warning("No records with valid coordinates found")
        return gpd.GeoDataFrame()

    df = pd.DataFrame(rows)
    geometry = [Point(r["_x"], r["_y"]) for r in rows]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS_DENMARK)
    gdf = gdf.drop(columns=["_x", "_y"], errors="ignore")

    logger.info("Created GeoDataFrame: %d features with point geometries", len(gdf))
    return gdf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("BBR & DAR DATA DOWNLOAD FOR NØRREBRO")
    logger.info("=" * 60)

    # Load study area boundary
    if not NORREBRO_BOUNDARY_FILE.exists():
        logger.error("Boundary file not found: %s", NORREBRO_BOUNDARY_FILE)
        sys.exit(1)

    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info(
        "Loaded boundary: %d features, %.2f km², CRS %s",
        len(boundary), boundary.geometry.area.sum() / 1e6, boundary.crs,
    )

    # --- BBR ---
    logger.info("-" * 60)
    logger.info("PART 1: BBR BUILDING ATTRIBUTES")
    logger.info("-" * 60)

    try:
        client = DatafordelerenClient()
        bbr = client.download_bbr(boundary)

        if not bbr.empty:
            BBR_RAW_DIR.mkdir(parents=True, exist_ok=True)
            bbr.to_file(BBR_OUTPUT_FILE, driver="GPKG")
            logger.info("Saved BBR: %s (%d buildings)", BBR_OUTPUT_FILE, len(bbr))

            # Show building use distribution if available
            use_col = BBR_KEY_ATTRIBUTES["use"]
            if use_col in bbr.columns:
                logger.info("Building use distribution (top 10):")
                for val, count in bbr[use_col].value_counts().head(10).items():
                    logger.info("  %s: %d", val, count)
        else:
            logger.warning("No BBR data retrieved")
    except requests.exceptions.HTTPError as e:
        logger.error("BBR HTTP error: %s", e)
        logger.error("Check your DATAFORDELEREN credentials in .env")
    except Exception as e:
        logger.error("BBR download failed: %s", e, exc_info=True)

    # --- DAR ---
    logger.info("-" * 60)
    logger.info("PART 2: DAR ACCESS POINTS")
    logger.info("-" * 60)

    try:
        dar = DARDownloader()
        muni = COPENHAGEN_MUNICIPALITY_CODE

        # Download Adressepunkt (per municipality)
        adressepunkt_path = dar.download_adressepunkt(muni)

        # Parse Adressepunkt → GeoDataFrame
        ap_records = parse_dar_archive(adressepunkt_path)
        if ap_records:
            ap_gdf = adressepunkt_to_geodataframe(ap_records)

            if not ap_gdf.empty:
                # Clip to Nørrebro boundary
                if ap_gdf.crs != boundary.crs:
                    boundary_reproj = boundary.to_crs(ap_gdf.crs)
                else:
                    boundary_reproj = boundary

                ap_cols = list(ap_gdf.columns)
                ap_clipped = gpd.sjoin(
                    ap_gdf, boundary_reproj[["geometry"]], how="inner", predicate="within"
                )
                ap_clipped = ap_clipped[[c for c in ap_cols if c in ap_clipped.columns]]

                logger.info("Adressepunkt: %d in Copenhagen → %d in Nørrebro", len(ap_gdf), len(ap_clipped))

                DAR_RAW_DIR.mkdir(parents=True, exist_ok=True)
                ap_clipped.to_file(DAR_ADRESSEPUNKT_OUTPUT, driver="GPKG")
                logger.info("Saved DAR adressepunkt: %s", DAR_ADRESSEPUNKT_OUTPUT)

        # Download Husnummer (national only — large file ~620 MB)
        # Skipping by default; uncomment to download if needed for BBR→address linking
        logger.info("Husnummer: skipped (national-only, ~620 MB). Uncomment in script to download.")

    except requests.exceptions.HTTPError as e:
        logger.error("DAR HTTP error: %s", e)
        logger.error("Check your DATAFORDELEREN credentials in .env")
    except Exception as e:
        logger.error("DAR download failed: %s", e, exc_info=True)

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)

    for path in [BBR_OUTPUT_FILE, DAR_ADRESSEPUNKT_OUTPUT]:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            logger.info("  %s (%.1f MB)", path, size_mb)
        else:
            logger.info("  %s — not created", path)


if __name__ == "__main__":
    main()
