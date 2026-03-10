"""
Download BBR Enhed (Dwelling Unit) data for Nørrebro

Downloads all dwelling unit records for Copenhagen municipality (0101) from
the BBR File Download API, then filters to buildings within Nørrebro.

Each Enhed record is one dwelling unit; units link back to their parent
building via the `bygning` field (= id_lokalId in the building layer).

Outputs:
    data/raw/bbr/norrebro_bbr_enhed.csv
        building_id, use_code, antal_boliger (residential units per building)

Credentials: DATAFORDELEREN_USERNAME and DATAFORDELEREN_PASSWORD in .env

Note: The Copenhagen Enhed file is ~96 MB (compressed). Download uses urllib
with a socket timeout to avoid mid-stream disconnects from requests/urllib3.

Usage:
    python scripts/download/download_bbr_enhed.py
"""

import json
import logging
import os
import socket
import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    BBR_ENHED_CSV,
    BBR_OUTPUT_FILE,
    BBR_RAW_DIR,
    COPENHAGEN_MUNICIPALITY_CODE,
    DATAFORDELER_FILE_DOWNLOAD_URL,
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

# Filter criteria
ENHED_STATUS_AKTUEL = "6"            # Only current/active units
ENHED_RESIDENTIAL_MIN = 110          # BBR residential use codes start at 110
ENHED_RESIDENTIAL_MAX = 190          # and end at 190

# Socket timeout for large file download
DOWNLOAD_SOCKET_TIMEOUT = 600  # seconds


def download_enhed_zip(username: str, password: str, municipality_code: str) -> bytes:
    """
    Download BBR Enhed ZIP file using urllib with socket-level timeout.

    Uses urllib instead of requests to avoid mid-transfer read timeouts
    that occur with the Datafordeler chunked responses for large files.
    """
    url = (
        f"{DATAFORDELER_FILE_DOWNLOAD_URL}"
        f"?username={username}&password={password}"
        f"&Register=BBR&LatestTotalForEntity=Enhed"
        f"&Type=Current&Format=JSON"
        f"&MunicipalityCode={municipality_code}"
    )

    socket.setdefaulttimeout(DOWNLOAD_SOCKET_TIMEOUT)

    logger.info("Downloading BBR Enhed (municipality %s)...", municipality_code)
    buf = BytesIO()
    total = 0

    with urllib.request.urlopen(url) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            buf.write(chunk)
            total += len(chunk)
            if total % (10 * 1024 * 1024) < 65536:
                logger.info("  %.0f MB downloaded...", total / 1e6)

    logger.info("Download complete: %.1f MB", total / 1e6)
    return buf.getvalue()


def parse_enhed_zip(raw_bytes: bytes) -> list[dict]:
    """Parse BBR Enhed ZIP bytes → list of records."""
    buf = BytesIO(raw_bytes)
    with zipfile.ZipFile(buf) as z:
        fname = z.namelist()[0]
        logger.info("Parsing %s...", fname)
        with z.open(fname) as f:
            records = json.load(f)
    logger.info("Parsed %d total Enhed records", len(records))
    return records


def filter_residential_aktuel(records: list[dict]) -> list[dict]:
    """Keep only current (status=6) residential units (use codes 110–190)."""
    filtered = []
    for r in records:
        if r.get("status") != ENHED_STATUS_AKTUEL:
            continue
        use = r.get("enh020EnhedensAnvendelse")
        if use is None:
            continue
        try:
            use_int = int(use)
        except (ValueError, TypeError):
            continue
        if ENHED_RESIDENTIAL_MIN <= use_int <= ENHED_RESIDENTIAL_MAX:
            filtered.append(r)
    logger.info(
        "After status=aktuel + residential filter: %d units", len(filtered)
    )
    return filtered


def aggregate_to_buildings(records: list[dict]) -> pd.DataFrame:
    """
    Aggregate unit records to building level.

    Returns DataFrame with columns:
        building_id   — BBR building id_lokalId
        antal_boliger — residential unit count
    """
    df = pd.DataFrame([
        {"building_id": r["bygning"], "use_code": r.get("enh020EnhedensAnvendelse")}
        for r in records
        if r.get("bygning")
    ])
    result = (
        df.groupby("building_id")
        .size()
        .reset_index(name="antal_boliger")
    )
    logger.info(
        "Aggregated to %d buildings: median %.0f units, max %d units",
        len(result),
        result["antal_boliger"].median(),
        result["antal_boliger"].max(),
    )
    return result


def main():
    logger.info("=" * 60)
    logger.info("BBR ENHED (DWELLING UNITS) DOWNLOAD FOR NØRREBRO")
    logger.info("=" * 60)

    username = os.getenv("DATAFORDELEREN_USERNAME")
    password = os.getenv("DATAFORDELEREN_PASSWORD")
    if not username or not password:
        logger.error(
            "Credentials not found. Set DATAFORDELEREN_USERNAME and "
            "DATAFORDELEREN_PASSWORD in .env"
        )
        sys.exit(1)

    # Load Nørrebro BBR buildings to get the set of valid building IDs
    if not BBR_OUTPUT_FILE.exists():
        logger.error("Raw BBR buildings not found: %s", BBR_OUTPUT_FILE)
        logger.error("Run scripts/download/download_bbr_dar.py first")
        sys.exit(1)

    if not NORREBRO_BOUNDARY_FILE.exists():
        logger.error("Boundary file not found: %s", NORREBRO_BOUNDARY_FILE)
        sys.exit(1)

    bbr_buildings = gpd.read_file(BBR_OUTPUT_FILE)
    norrebro_ids = set(bbr_buildings["id_lokalId"].dropna())
    logger.info("Nørrebro buildings in BBR: %d", len(norrebro_ids))

    # Use cached file if it exists
    if BBR_ENHED_CSV.exists():
        size_kb = BBR_ENHED_CSV.stat().st_size / 1024
        logger.info(
            "Using cached Enhed CSV (%.0f KB): %s", size_kb, BBR_ENHED_CSV.name
        )
        result = pd.read_csv(BBR_ENHED_CSV)
        logger.info("Loaded %d building unit records", len(result))
    else:
        # Download full Copenhagen Enhed file
        raw_bytes = download_enhed_zip(
            username, password, COPENHAGEN_MUNICIPALITY_CODE
        )

        # Parse and filter
        all_records = parse_enhed_zip(raw_bytes)
        residential = filter_residential_aktuel(all_records)

        # Filter to Nørrebro buildings only
        norrebro_units = [r for r in residential if r.get("bygning") in norrebro_ids]
        logger.info(
            "Nørrebro residential units: %d (of %d Copenhagen-wide)",
            len(norrebro_units), len(residential)
        )

        # Aggregate to building-level counts
        result = aggregate_to_buildings(norrebro_units)

        # Save
        BBR_RAW_DIR.mkdir(parents=True, exist_ok=True)
        result.to_csv(BBR_ENHED_CSV, index=False)
        size_kb = BBR_ENHED_CSV.stat().st_size / 1024
        logger.info(
            "Saved: %s (%.0f KB, %d buildings)",
            BBR_ENHED_CSV, size_kb, len(result)
        )

    # Summary
    logger.info("-" * 40)
    logger.info("Buildings with unit count: %d / %d Nørrebro BBR buildings",
                len(result), len(norrebro_ids))
    logger.info("Total residential units: %d", result["antal_boliger"].sum())
    logger.info(
        "Units per building: min=%d, median=%.0f, max=%d",
        result["antal_boliger"].min(),
        result["antal_boliger"].median(),
        result["antal_boliger"].max(),
    )
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE → %s", BBR_ENHED_CSV)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
