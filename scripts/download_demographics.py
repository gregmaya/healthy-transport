"""
Download demographic data for Copenhagen districts from Copenhagen StatBank.

This script downloads population and demographic statistics for Copenhagen's
10 districts (bydele) from Copenhagen Municipality's StatBank (kk.statistikbank.dk).

Data sources:
- Copenhagen StatBank (kk.statistikbank.dk) - Official municipal statistics
- OpenData.dk - Pre-processed demographic datasets
- Statistics Denmark API - National statistics (if needed)

Usage:
    python scripts/download_demographics.py
    python scripts/download_demographics.py --table KKBEF8 --output data/raw/population
    python scripts/download_demographics.py --source opendata
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data sources
STATBANK_BASE_URL = "https://kk.statistikbank.dk/statbank5a"
OPENDATA_SEARCH_URL = "https://www.opendata.dk/api/3/action/package_search"
DST_API_URL = "https://api.statbank.dk/v1/data"

# Copenhagen districts
COPENHAGEN_DISTRICTS = [
    "Indre By",
    "Østerbro",
    "Nørrebro",
    "Vesterbro/Kongens Enghave",
    "Valby",
    "Vanløse",
    "Brønshøj-Husum",
    "Bispebjerg",
    "Amager Øst",
    "Amager Vest"
]

# Common demographic tables in Copenhagen StatBank
STATBANK_TABLES = {
    'KKBEF8': 'Population by district, sex, age and citizenship',
    'KKBEF9': 'Population by district, marital status and citizenship',
    'KKBEF10': 'Households by district, household type and size',
    'KKBEF11': 'Population by district and place of birth',
}


def search_opendata_demographics() -> list:
    """
    Search OpenData.dk for Copenhagen demographic datasets.

    Returns:
        list: Available demographic datasets
    """
    logger.info("Searching OpenData.dk for demographic data...")

    search_terms = [
        "copenhagen befolkning bydel",
        "copenhagen demographics district",
        "københavn statistik bydele"
    ]

    datasets = []

    for term in search_terms:
        try:
            params = {
                'q': term,
                'fq': 'organization:city-of-copenhagen',
                'rows': 20
            }

            response = requests.get(
                OPENDATA_SEARCH_URL,
                params=params,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                if 'result' in results and 'results' in results['result']:
                    datasets.extend(results['result']['results'])
                    logger.info(f"  Found {len(results['result']['results'])} datasets for '{term}'")
            else:
                logger.warning(f"Search failed for '{term}': {response.status_code}")

        except Exception as e:
            logger.warning(f"Search error for '{term}': {e}")
            continue

    # Deduplicate
    unique_datasets = {d['id']: d for d in datasets}.values()
    logger.info(f"\n✓ Found {len(unique_datasets)} unique demographic datasets")

    return list(unique_datasets)


def display_available_datasets(datasets: list):
    """Display available demographic datasets."""
    logger.info("\n" + "="*70)
    logger.info("AVAILABLE DEMOGRAPHIC DATASETS")
    logger.info("="*70)

    for i, dataset in enumerate(datasets, 1):
        logger.info(f"\n{i}. {dataset.get('title', 'No title')}")
        logger.info(f"   ID: {dataset.get('name', 'N/A')}")

        if 'notes' in dataset and dataset['notes']:
            notes = dataset['notes'][:150] + "..." if len(dataset['notes']) > 150 else dataset['notes']
            logger.info(f"   Description: {notes}")

        if 'resources' in dataset:
            logger.info(f"   Resources: {len(dataset['resources'])} files available")
            for res in dataset['resources'][:3]:  # Show first 3 resources
                format_type = res.get('format', 'unknown')
                name = res.get('name', res.get('url', 'unnamed'))
                logger.info(f"     - {name} ({format_type})")

    logger.info("="*70 + "\n")


def download_from_opendata(dataset_id: str, output_dir: Path) -> list:
    """
    Download demographic data from OpenData.dk dataset.

    Args:
        dataset_id: Dataset identifier
        output_dir: Output directory

    Returns:
        list: Downloaded file paths
    """
    logger.info(f"Downloading dataset: {dataset_id}")

    # Get dataset details
    try:
        response = requests.get(
            f"https://www.opendata.dk/api/3/action/package_show",
            params={'id': dataset_id},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get dataset details: {response.status_code}")

        dataset_info = response.json()['result']

    except Exception as e:
        logger.error(f"Failed to get dataset info: {e}")
        raise

    # Download resources
    downloaded_files = []
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for resource in dataset_info.get('resources', []):
        try:
            url = resource.get('url')
            format_type = resource.get('format', 'unknown').lower()
            name = resource.get('name', f"resource_{resource.get('id', 'unknown')}")

            # Sanitize filename
            filename = f"{name}.{format_type}".replace(' ', '_').replace('/', '_')
            output_file = output_dir / filename

            logger.info(f"  Downloading: {name} ({format_type})")

            # Download file
            file_response = requests.get(url, timeout=60)
            file_response.raise_for_status()

            output_file.write_bytes(file_response.content)
            downloaded_files.append(output_file)

            logger.info(f"  ✓ Saved to: {output_file}")
            logger.info(f"    Size: {output_file.stat().st_size / 1024:.2f} KB")

        except Exception as e:
            logger.warning(f"  Failed to download {name}: {e}")
            continue

    return downloaded_files


def create_statbank_instructions(output_dir: Path):
    """
    Create instructions file for manual StatBank download.

    Args:
        output_dir: Output directory
    """
    instructions = """
# Copenhagen StatBank Manual Download Instructions

Copenhagen Municipality's StatBank (kk.statistikbank.dk) contains detailed
demographic statistics by district (bydel).

## Recommended Tables

### 1. KKBEF8 - Population by district, sex, age and citizenship
URL: https://kk.statistikbank.dk/statbank5a/SelectVarVal/Define.asp?Maintable=KKBEF8&PLanguage=1

Variables:
- District (Bydel): Select all 10 districts
- Sex (Køn): Select all
- Age (Alder): Select relevant age groups or all
- Citizenship (Statsborgerskab): Select relevant categories
- Time (Tid): Select latest year or time series

### 2. KKBEF10 - Households by district, household type and size
URL: https://kk.statistikbank.dk/statbank5a/SelectVarVal/Define.asp?Maintable=KKBEF10&PLanguage=1

### 3. KKBEF11 - Population by district and place of birth
URL: https://kk.statistikbank.dk/statbank5a/SelectVarVal/Define.asp?Maintable=KKBEF11&PLanguage=1

## Download Steps

1. **Visit the table URL** (e.g., KKBEF8)

2. **Select variables:**
   - Check boxes for desired categories
   - Ensure "Bydel" (District) includes all 10 districts
   - Select latest time period

3. **Continue** and view the table

4. **Download options** (top right corner):
   - CSV (semicolon separated)
   - Excel
   - PC-Axis

5. **Recommended format:** CSV or Excel

6. **Save files** to: `data/raw/population/manual_downloads/`

7. **Process with Python:**
   ```python
   import pandas as pd

   # Load CSV (Danish format uses semicolon)
   df = pd.read_csv('KKBEF8_data.csv', sep=';', encoding='latin1')

   # Process and clean data
   # ... (see processing script)
   ```

## File Naming Convention

Save downloaded files as:
- `KKBEF8_population_sex_age_citizenship_YYYYMMDD.csv`
- `KKBEF10_households_type_size_YYYYMMDD.csv`
- `KKBEF11_population_birthplace_YYYYMMDD.csv`

## Processing Script

After download, process with:
```bash
python scripts/process_statbank_csv.py data/raw/population/manual_downloads/*.csv
```

## Contact

For questions about data:
- Email: bydata@kk.dk
- Website: https://kk.statistikbank.dk

## Alternative: OpenData.dk

Search for pre-processed demographic datasets:
https://www.opendata.dk/city-of-copenhagen

Look for:
- "befolkning" (population)
- "bydel" (district)
- "demografi" (demographics)
"""

    instructions_file = output_dir / "STATBANK_DOWNLOAD_INSTRUCTIONS.md"
    instructions_file.write_text(instructions)

    logger.info(f"\n✓ Created instructions file: {instructions_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--source',
        choices=['opendata', 'statbank', 'both'],
        default='both',
        help='Data source (default: both)'
    )
    parser.add_argument(
        '--table',
        default='KKBEF8',
        help='StatBank table ID (default: KKBEF8)'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('data/raw/population'),
        help='Output directory (default: data/raw/population)'
    )
    parser.add_argument(
        '--search-only',
        action='store_true',
        help='Only search and display available datasets'
    )

    args = parser.parse_args()

    try:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("\n" + "="*70)
        logger.info("COPENHAGEN DEMOGRAPHICS DOWNLOADER")
        logger.info("="*70)
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Data source: {args.source}")
        logger.info("="*70 + "\n")

        # Search OpenData.dk
        if args.source in ['opendata', 'both']:
            datasets = search_opendata_demographics()

            if datasets:
                display_available_datasets(datasets)

                if args.search_only:
                    logger.info("\nTo download a specific dataset:")
                    logger.info("  python scripts/download_demographics.py --dataset <dataset-name>")
                    return 0

                # Optionally download first relevant dataset
                # (In production, you'd want user to select)
                logger.info("\nNote: Automatic download not implemented yet.")
                logger.info("Please review available datasets and download manually from:")
                logger.info("  https://www.opendata.dk/city-of-copenhagen")

        # Create StatBank instructions
        if args.source in ['statbank', 'both']:
            logger.info("\nCreating Copenhagen StatBank download instructions...")
            create_statbank_instructions(output_dir)

            logger.info("\n" + "="*70)
            logger.info("COPENHAGEN STATBANK TABLES")
            logger.info("="*70)
            for table_id, description in STATBANK_TABLES.items():
                logger.info(f"\n{table_id}: {description}")
                logger.info(f"  URL: {STATBANK_BASE_URL}/SelectVarVal/Define.asp?Maintable={table_id}&PLanguage=1")
            logger.info("="*70)

        logger.info("\n✓ Setup complete!")
        logger.info("\nNext steps:")
        logger.info("  1. Review STATBANK_DOWNLOAD_INSTRUCTIONS.md")
        logger.info("  2. Visit Copenhagen StatBank and download KKBEF8 table")
        logger.info("  3. Save CSV files to data/raw/population/manual_downloads/")
        logger.info("  4. Process with: python scripts/process_statbank_csv.py")
        logger.info("\nFor assistance: bydata@kk.dk")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
