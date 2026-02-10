"""
Import and process manually downloaded Copenhagen districts data.

If the download script fails due to network restrictions, you can manually
download the data and use this script to process it.

Usage:
    python scripts/import_manual_download.py <input_file>
    python scripts/import_manual_download.py bydel.geojson
    python scripts/import_manual_download.py bydel.geojson --output data/raw/boundary
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Danish CRS
CRS_DENMARK = "EPSG:25832"  # ETRS89 / UTM zone 32N
CRS_WGS84 = "EPSG:4326"


def load_file(input_path: Path) -> gpd.GeoDataFrame:
    """
    Load geospatial file (GeoJSON, Shapefile, etc.).

    Args:
        input_path: Path to input file

    Returns:
        GeoDataFrame with district boundaries
    """
    logger.info(f"Loading file: {input_path}")

    try:
        gdf = gpd.read_file(input_path)
        logger.info(f"✓ Loaded {len(gdf)} features")
        logger.info(f"  Original CRS: {gdf.crs}")
        logger.info(f"  Columns: {gdf.columns.tolist()}")

        return gdf

    except Exception as e:
        logger.error(f"Failed to load file: {e}")
        raise


def process_districts(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Process and standardize district data.

    Args:
        gdf: Input GeoDataFrame

    Returns:
        Processed GeoDataFrame
    """
    logger.info("Processing district data...")

    # Reproject to Danish CRS if needed
    if gdf.crs and gdf.crs.to_string() != CRS_DENMARK:
        logger.info(f"Reprojecting from {gdf.crs} to {CRS_DENMARK}")
        gdf = gdf.to_crs(CRS_DENMARK)

    # Clean column names (lowercase, remove special chars)
    gdf.columns = gdf.columns.str.lower().str.replace(' ', '_')

    # Display district information
    name_cols = [col for col in gdf.columns if 'navn' in col or 'name' in col]
    if name_cols:
        logger.info(f"\nDistricts found:")
        for idx, row in gdf.iterrows():
            district_name = row[name_cols[0]]
            area_km2 = row.geometry.area / 1_000_000
            logger.info(f"  - {district_name}: {area_km2:.2f} km²")

    return gdf


def save_data(gdf: gpd.GeoDataFrame, output_dir: Path, format: str = 'gpkg'):
    """
    Save processed data to file.

    Args:
        gdf: GeoDataFrame to save
        output_dir: Output directory
        format: Output format
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d')

    if format == 'gpkg':
        output_file = output_dir / f"kk_copenhagen_bydele_{today}.gpkg"
        gdf.to_file(output_file, driver='GPKG', layer='copenhagen_districts')
    elif format == 'geojson':
        output_file = output_dir / f"kk_copenhagen_bydele_{today}.geojson"
        gdf.to_file(output_file, driver='GeoJSON')
    elif format == 'shp':
        output_file = output_dir / f"kk_copenhagen_bydele_{today}.shp"
        gdf.to_file(output_file, driver='ESRI Shapefile')
    else:
        raise ValueError(f"Unsupported format: {format}")

    logger.info(f"\n✓ Saved to: {output_file}")
    logger.info(f"  File size: {output_file.stat().st_size / 1024:.2f} KB")
    logger.info(f"  CRS: {gdf.crs}")

    return output_file


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Input file (GeoJSON, Shapefile, etc.)'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('data/raw/boundary'),
        help='Output directory (default: data/raw/boundary)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['gpkg', 'geojson', 'shp'],
        default='gpkg',
        help='Output format (default: gpkg)'
    )

    args = parser.parse_args()

    # Check input file exists
    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        return 1

    try:
        # Load and process
        gdf = load_file(args.input_file)
        gdf = process_districts(gdf)

        # Summary
        logger.info("\n" + "="*60)
        logger.info("COPENHAGEN DISTRICTS SUMMARY")
        logger.info("="*60)
        logger.info(f"Total districts: {len(gdf)}")
        logger.info(f"Total area: {gdf.geometry.area.sum() / 1_000_000:.2f} km²")
        logger.info(f"CRS: {gdf.crs}")
        logger.info("="*60 + "\n")

        # Save
        output_file = save_data(gdf, args.output, args.format)

        logger.info("\n✓ Import complete!")
        logger.info("\nNext steps:")
        logger.info("  1. Open in QGIS to explore the districts")
        logger.info("  2. Identify the Nørrebro district polygon")
        logger.info("  3. Extract Nørrebro boundary for clipping other datasets")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
