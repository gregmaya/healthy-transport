"""
Download Health Data for Nørrebro Analysis

Automates download of StatBank Denmark tables (causes of death, deaths by
municipality) via their public API. Also verifies existence of manually
downloaded files (eSundhed chronic disease data, Sundhedsprofil indicators,
WHO HEAT user guide).

See docs/health_data_download_guide.md for step-by-step manual download
instructions for all 5 health data sources.

Outputs:
- data/raw/health/statbank_doda1_causes_of_death.csv  (automated)
- data/raw/health/statbank_fod207_deaths_by_municipality.csv  (automated)
- Verification of manual files:
  - data/raw/health/esundhed_kroniske_sygdomme_2010_2025.xlsx
  - data/raw/health/copenhagen_sundhedsprofil_indicators.csv
  - data/raw/health/WHO_HEAT_user_guide_2024.pdf

Usage:
    python scripts/download/download_health.py
"""

import logging
import sys
from pathlib import Path

import requests

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    HEALTH_RAW_DIR,
    HEALTH_DODA1_FILE,
    HEALTH_FOD207_FILE,
    HEALTH_ESUNDHED_FILE,
    HEALTH_SUNDHEDSPROFIL_FILE,
    HEALTH_HEAT_GUIDE_FILE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# StatBank Denmark API
STATBANK_API_URL = "https://api.statbank.dk/v1/data"


# ---------------------------------------------------------------------------
# StatBank API downloads
# ---------------------------------------------------------------------------


def download_statbank_table(table_id, variables, output_path, description):
    """Download a table from StatBank Denmark API as CSV.

    Parameters
    ----------
    table_id : str
        StatBank table ID (e.g., "DODA1", "FOD207")
    variables : list[dict]
        Variable selection for the API request. Each dict has "code" and "values".
    output_path : Path
        Where to save the CSV file.
    description : str
        Human-readable description for logging.
    """
    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        logger.info(
            "%s already exists: %s (%.1f KB)", description, output_path, size_kb
        )
        logger.info("Delete the file and re-run to download a fresh copy.")
        return

    logger.info("Downloading %s (table %s) from StatBank Denmark...", description, table_id)

    payload = {
        "table": table_id,
        "format": "CSV",
        "lang": "en",
        "variables": variables,
    }

    response = requests.post(STATBANK_API_URL, json=payload, timeout=120)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)

    size_kb = output_path.stat().st_size / 1024
    line_count = response.text.count("\n")
    logger.info("Downloaded %s: %.1f KB, %d lines", output_path.name, size_kb, line_count)


def download_doda1():
    """Download DODA1: causes of death by cause, age, sex (national level)."""
    variables = [
        {"code": "ÅRSAG", "values": ["*"]},  # All cause-of-death categories
        {"code": "ALDER", "values": ["*"]},  # All age groups
        {"code": "KØN", "values": ["*"]},  # All sexes (total, male, female)
        {"code": "Tid", "values": ["*"]},  # All years
    ]
    download_statbank_table(
        table_id="DODA1",
        variables=variables,
        output_path=HEALTH_DODA1_FILE,
        description="Causes of death (DODA1)",
    )


def download_fod207():
    """Download FOD207: deaths by municipality, age, sex.

    Selects Copenhagen (101), Region Hovedstaden (084), and national total (000)
    to keep the file manageable while providing the comparisons we need.
    """
    variables = [
        {
            "code": "OMRÅDE",
            "values": [
                "000",  # Hele landet (all of Denmark)
                "084",  # Region Hovedstaden
                "101",  # København municipality
            ],
        },
        {"code": "ALDER", "values": ["*"]},  # All individual ages (0-99) + total
        {"code": "KØN", "values": ["*"]},  # Male + Female
        {"code": "Tid", "values": ["*"]},  # All years (2006-2025)
    ]
    download_statbank_table(
        table_id="FOD207",
        variables=variables,
        output_path=HEALTH_FOD207_FILE,
        description="Deaths by municipality (FOD207)",
    )


# ---------------------------------------------------------------------------
# Manual file verification
# ---------------------------------------------------------------------------

MANUAL_FILES = [
    (
        HEALTH_ESUNDHED_FILE,
        "eSundhed chronic disease register (Source 1)",
        "https://sundhedsdatabank.dk/sygdomme/kroniske-sygdomme-og-svaere-psykiske-lidelser",
    ),
    (
        HEALTH_SUNDHEDSPROFIL_FILE,
        "Danskernes Sundhed indicators (Source 2)",
        "https://www.danskernessundhed.dk/",
    ),
    (
        HEALTH_HEAT_GUIDE_FILE,
        "WHO HEAT user guide 2024 (Source 5)",
        "https://www.who.int/europe/publications/i/item/9789289058377",
    ),
]


def verify_manual_files():
    """Check that manually downloaded files exist and report status."""
    logger.info("-" * 60)
    logger.info("MANUAL FILE VERIFICATION")
    logger.info("-" * 60)

    all_present = True
    for filepath, description, url in MANUAL_FILES:
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            logger.info("[OK] %s (%.1f KB)", description, size_kb)
        else:
            logger.warning("[MISSING] %s", description)
            logger.warning("  Download from: %s", url)
            logger.warning("  Save to: %s", filepath)
            all_present = False

    if not all_present:
        logger.info("")
        logger.info(
            "See docs/health_data_download_guide.md for detailed download instructions."
        )

    return all_present


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("HEALTH DATA DOWNLOAD")
    logger.info("=" * 60)

    # Create output directory
    HEALTH_RAW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", HEALTH_RAW_DIR)

    # Automated downloads from StatBank Denmark API
    logger.info("-" * 60)
    logger.info("STATBANK DENMARK API DOWNLOADS")
    logger.info("-" * 60)

    download_doda1()
    download_fod207()

    # Verify manual downloads
    verify_manual_files()

    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
