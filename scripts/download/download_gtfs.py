"""
Download Rejseplanen GTFS Feed for Denmark

Downloads the national GTFS zip from Rejseplanen Labs containing all Danish
public transport data (buses, metro, trains, ferries). The zip is saved as-is
with no extraction or processing.

Outputs:
- data/raw/transport/rejseplanen_gtfs.zip

Usage:
    python scripts/download_gtfs.py
"""

import logging
import sys
from pathlib import Path

import requests

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    GTFS_DOWNLOAD_URL,
    GTFS_ZIP_FILE,
    TRANSPORT_RAW_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def download_gtfs(url, output_path):
    """Download the GTFS zip file from Rejseplanen."""
    logger.info("Downloading GTFS feed from %s", url)

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            total_bytes += len(chunk)

    size_mb = total_bytes / (1024 * 1024)
    logger.info("Downloaded %.1f MB to %s", size_mb, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("GTFS FEED DOWNLOAD")
    logger.info("=" * 60)

    # Check if file already exists
    if GTFS_ZIP_FILE.exists():
        size_mb = GTFS_ZIP_FILE.stat().st_size / (1024 * 1024)
        logger.info("GTFS zip already exists: %s (%.1f MB)", GTFS_ZIP_FILE, size_mb)
        logger.info("Delete the file and re-run to download a fresh copy.")
        return

    download_gtfs(GTFS_DOWNLOAD_URL, GTFS_ZIP_FILE)

    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
