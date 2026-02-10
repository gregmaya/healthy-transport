"""
Download Copenhagen districts (bydele) from OpenData.dk.

This script downloads the official Copenhagen municipality districts,
including Nørrebro, and saves them as a GeoPackage file.

Usage:
    python scripts/download_copenhagen_districts.py
    python scripts/download_copenhagen_districts.py --format geojson
    python scripts/download_copenhagen_districts.py --output data/raw/boundary/
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely import wkt
from shapely.geometry import shape

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API Configuration
CKAN_API_URL = "https://admin.opendata.dk/api/3/action/datastore_search_sql"
RESOURCE_ID = "49564091-ccf9-4f7b-8d32-12d98fe57def"

# Alternative direct download URLs
ALTERNATIVE_URLS = {
    "geojson": f"https://admin.opendata.dk/api/3/action/datastore_search?resource_id={RESOURCE_ID}&limit=1000",
    "shapefile": "https://www.opendata.dk/city-of-copenhagen/bydele",
    "wfs": "https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:bydel&outputFormat=json&SRSNAME=EPSG:4326",
}

# Danish CRS
CRS_DENMARK = "EPSG:25832"  # ETRS89 / UTM zone 32N


def download_from_ckan_api(sql_query: str = None) -> dict:
    """
    Download data from CKAN API using SQL query.

    Args:
        sql_query: SQL query string. If None, defaults to SELECT * query.

    Returns:
        dict: API response data
    """
    if sql_query is None:
        sql_query = f'SELECT * from "{RESOURCE_ID}"'

    logger.info("Attempting to download from CKAN API...")
    logger.debug(f"SQL Query: {sql_query}")

    # Try with different headers
    headers_options = [
        {"User-Agent": "Mozilla/5.0 (compatible; GeoDataDownloader/1.0)"},
        {"User-Agent": "curl/7.68.0"},
        {},  # No special headers
    ]

    for headers in headers_options:
        try:
            params = {"sql": sql_query}
            response = requests.get(
                CKAN_API_URL, params=params, headers=headers, timeout=30
            )

            if response.status_code == 200:
                logger.info("✓ Successfully downloaded data from CKAN API")
                return response.json()
            else:
                logger.warning(
                    f"Attempt with headers {headers} failed: {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed with headers {headers}: {e}")
            continue

    raise Exception("All CKAN API download attempts failed")


def download_from_datastore_search() -> dict:
    """
    Alternative method: Download using datastore_search endpoint.

    Returns:
        dict: API response data
    """
    logger.info("Attempting alternative download method (datastore_search)...")

    url = "https://admin.opendata.dk/api/3/action/datastore_search"
    params = {
        "resource_id": RESOURCE_ID,
        "limit": 1000,  # Ensure we get all districts
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GeoDataDownloader/1.0)",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info("✓ Successfully downloaded using datastore_search")
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"datastore_search method failed: {e}")
        raise


def download_from_wfs() -> gpd.GeoDataFrame:
    """
    Download using WFS (Web Feature Service) - most reliable method.

    Returns:
        GeoDataFrame: District boundaries
    """
    logger.info("Attempting WFS download...")

    wfs_url = ALTERNATIVE_URLS["wfs"]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GeoDataDownloader/1.0)",
    }

    try:
        response = requests.get(wfs_url, headers=headers, timeout=60)
        response.raise_for_status()

        geojson_data = response.json()
        gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        gdf = gdf.to_crs(CRS_DENMARK)

        logger.info(f"✓ Successfully downloaded {len(gdf)} districts via WFS")
        return gdf

    except Exception as e:
        logger.error(f"WFS download failed: {e}")
        raise


def parse_geometry(geom_data):
    """
    Parse geometry from various formats (WKT, GeoJSON, etc.).

    Args:
        geom_data: Geometry data in string or dict format

    Returns:
        Shapely geometry object
    """
    if geom_data is None:
        return None

    # Try parsing as WKT
    if isinstance(geom_data, str):
        try:
            return wkt.loads(geom_data)
        except Exception:
            pass

        # Try parsing as JSON string
        try:
            geom_dict = json.loads(geom_data)
            return shape(geom_dict)
        except Exception:
            pass

    # Try parsing as GeoJSON dict
    if isinstance(geom_data, dict):
        try:
            return shape(geom_data)
        except Exception:
            pass

    logger.warning(f"Could not parse geometry: {type(geom_data)}")
    return None


def process_api_response(api_data: dict) -> gpd.GeoDataFrame:
    """
    Process API response and convert to GeoDataFrame.

    Args:
        api_data: Response from CKAN API

    Returns:
        GeoDataFrame with district boundaries
    """
    logger.info("Processing API response...")

    # Extract records from different response structures
    if "result" in api_data:
        if "records" in api_data["result"]:
            records = api_data["result"]["records"]
        elif isinstance(api_data["result"], list):
            records = api_data["result"]
        else:
            raise ValueError(
                f"Unexpected result structure: {api_data['result'].keys()}"
            )
    else:
        raise ValueError("No 'result' key in API response")

    if not records:
        raise ValueError("No records found in API response")

    logger.info(f"Found {len(records)} records")
    logger.debug(f"Sample record keys: {records[0].keys()}")

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Find geometry column (common names)
    geom_columns = ["geom", "geometry", "wkt_geom", "the_geom", "GEOMETRI", "geometri"]
    geom_col = None

    for col in geom_columns:
        if col in df.columns:
            geom_col = col
            break

    if geom_col is None:
        logger.warning(
            f"No geometry column found. Available columns: {df.columns.tolist()}"
        )
        logger.info("Attempting to create GeoDataFrame without geometry...")
        # Return DataFrame as-is if no geometry found
        return df

    logger.info(f"Using geometry column: {geom_col}")

    # Parse geometries
    df["geometry"] = df[geom_col].apply(parse_geometry)

    # Remove invalid geometries
    valid_geoms = df["geometry"].notna()
    if not valid_geoms.all():
        logger.warning(f"Removing {(~valid_geoms).sum()} records with invalid geometry")
        df = df[valid_geoms]

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry="geometry")

    # Set CRS (assume EPSG:25832 for Danish data)
    if gdf.crs is None:
        logger.info(f"Setting CRS to {CRS_DENMARK}")
        gdf.set_crs(CRS_DENMARK, inplace=True)

    # Clean up column names
    if geom_col != "geometry":
        gdf = gdf.drop(columns=[geom_col])

    logger.info(f"✓ Created GeoDataFrame with {len(gdf)} districts")
    logger.info(f"  CRS: {gdf.crs}")
    logger.info(f"  Columns: {gdf.columns.tolist()}")

    return gdf


def save_geodata(gdf: gpd.GeoDataFrame, output_dir: Path, format: str = "gpkg"):
    """
    Save GeoDataFrame to file.

    Args:
        gdf: GeoDataFrame to save
        output_dir: Output directory path
        format: Output format ('gpkg', 'geojson', 'shp')
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")

    if format == "gpkg":
        output_file = output_dir / f"opendata_copenhagen_bydele_{today}.gpkg"
        gdf.to_file(output_file, driver="GPKG", layer="copenhagen_districts")
    elif format == "geojson":
        output_file = output_dir / f"opendata_copenhagen_bydele_{today}.geojson"
        gdf.to_file(output_file, driver="GeoJSON")
    elif format == "shp":
        output_file = output_dir / f"opendata_copenhagen_bydele_{today}.shp"
        gdf.to_file(output_file, driver="ESRI Shapefile")
    else:
        raise ValueError(f"Unsupported format: {format}")

    logger.info(f"✓ Saved to: {output_file}")
    logger.info(f"  File size: {output_file.stat().st_size / 1024:.2f} KB")

    return output_file


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/raw/boundary"),
        help="Output directory (default: data/raw/boundary)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["gpkg", "geojson", "shp"],
        default="gpkg",
        help="Output format (default: gpkg)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Try WFS first (most reliable)
        try:
            gdf = download_from_wfs()
        except Exception as e:
            logger.warning(f"WFS download failed: {e}")
            logger.info("Trying CKAN API methods...")

            # Try CKAN SQL query
            try:
                api_data = download_from_ckan_api()
            except Exception as e2:
                logger.warning(f"CKAN SQL API failed: {e2}")
                logger.info("Trying datastore_search...")
                api_data = download_from_datastore_search()

            # Process the data
            gdf = process_api_response(api_data)

        # Display summary
        logger.info("\n" + "=" * 60)
        logger.info("COPENHAGEN DISTRICTS SUMMARY")
        logger.info("=" * 60)
        if "geometry" in gdf.columns:
            logger.info(f"Total districts: {len(gdf)}")
            if "bydel_navn" in gdf.columns:
                logger.info(
                    f"Districts: {', '.join(sorted(gdf['bydel_navn'].tolist()))}"
                )
            elif "navn" in gdf.columns:
                logger.info(f"Districts: {', '.join(sorted(gdf['navn'].tolist()))}")
            logger.info(f"Total area: {gdf.geometry.area.sum() / 1_000_000:.2f} km²")
        logger.info("=" * 60 + "\n")

        # Save to file
        output_file = save_geodata(gdf, args.output, args.format)

        logger.info("\n✓ Download complete!")
        logger.info(f"  Output: {output_file}")
        logger.info("\nNext steps:")
        logger.info("  1. Open in QGIS to explore the districts")
        logger.info("  2. Identify the Nørrebro district")
        logger.info("  3. Update CLAUDE.MD checklist")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=args.verbose)
        logger.error("\nTroubleshooting:")
        logger.error("  1. Check your internet connection")
        logger.error("  2. Try running with --verbose flag for more details")
        logger.error("  3. Visit https://www.opendata.dk/city-of-copenhagen/bydele")
        logger.error("     to download manually if needed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
