"""
Process CSV files downloaded from Copenhagen StatBank.

This script processes demographic data downloaded from kk.statistikbank.dk
and converts it into clean, analysis-ready formats.

Usage:
    python scripts/process_statbank_csv.py <csv_file>
    python scripts/process_statbank_csv.py data/raw/population/manual_downloads/*.csv
    python scripts/process_statbank_csv.py KKBEF8_data.csv --output data/processed/
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Copenhagen districts (English/Danish mappings)
DISTRICT_MAPPING = {
    'Indre By': 'Indre By',
    'Østerbro': 'Østerbro',
    'Nørrebro': 'Nørrebro',
    'Vesterbro/Kongens Enghave': 'Vesterbro/Kongens Enghave',
    'Valby': 'Valby',
    'Vanløse': 'Vanløse',
    'Brønshøj-Husum': 'Brønshøj-Husum',
    'Bispebjerg': 'Bispebjerg',
    'Amager Øst': 'Amager Øst',
    'Amager Vest': 'Amager Vest',
}


def detect_encoding(file_path: Path) -> str:
    """
    Detect file encoding (Danish StatBank often uses latin1 or utf-8).

    Args:
        file_path: Path to CSV file

    Returns:
        str: Detected encoding
    """
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # Try reading first 1KB
            logger.debug(f"  Detected encoding: {encoding}")
            return encoding
        except UnicodeDecodeError:
            continue

    logger.warning("  Could not detect encoding, defaulting to latin1")
    return 'latin1'


def detect_separator(file_path: Path, encoding: str) -> str:
    """
    Detect CSV separator (Danish CSVs often use semicolon).

    Args:
        file_path: Path to CSV file
        encoding: File encoding

    Returns:
        str: Detected separator
    """
    with open(file_path, 'r', encoding=encoding) as f:
        first_line = f.readline()

    # Count occurrences
    comma_count = first_line.count(',')
    semicolon_count = first_line.count(';')
    tab_count = first_line.count('\t')

    if semicolon_count > comma_count and semicolon_count > tab_count:
        logger.debug("  Detected separator: semicolon (;)")
        return ';'
    elif tab_count > comma_count and tab_count > semicolon_count:
        logger.debug("  Detected separator: tab")
        return '\t'
    else:
        logger.debug("  Detected separator: comma (,)")
        return ','


def load_statbank_csv(file_path: Path) -> pd.DataFrame:
    """
    Load CSV file from Copenhagen StatBank with proper encoding/separator.

    Args:
        file_path: Path to CSV file

    Returns:
        DataFrame with loaded data
    """
    logger.info(f"Loading: {file_path.name}")

    # Detect encoding and separator
    encoding = detect_encoding(file_path)
    separator = detect_separator(file_path, encoding)

    # Load CSV
    try:
        df = pd.read_csv(
            file_path,
            sep=separator,
            encoding=encoding,
            thousands='.',  # Danish number format
            decimal=',',    # Danish decimal separator
        )

        logger.info(f"  ✓ Loaded {len(df)} rows × {len(df.columns)} columns")
        logger.debug(f"  Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        logger.error(f"  Failed to load {file_path}: {e}")
        raise


def clean_statbank_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize StatBank data.

    Args:
        df: Raw DataFrame from StatBank

    Returns:
        Cleaned DataFrame
    """
    logger.info("Cleaning data...")

    # Make a copy
    df_clean = df.copy()

    # Standardize column names
    df_clean.columns = (
        df_clean.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace('æ', 'ae')
        .str.replace('ø', 'oe')
        .str.replace('å', 'aa')
    )

    # Find district column (bydel)
    district_cols = [col for col in df_clean.columns if 'bydel' in col or 'district' in col]
    if district_cols:
        district_col = district_cols[0]
        logger.info(f"  Found district column: {district_col}")

        # Standardize district names
        df_clean[district_col] = df_clean[district_col].str.strip()

        # Report districts found
        districts_found = df_clean[district_col].unique()
        logger.info(f"  Districts in data: {len(districts_found)}")
        for district in sorted(districts_found):
            count = len(df_clean[df_clean[district_col] == district])
            logger.info(f"    - {district}: {count} records")

    # Find time/year column
    time_cols = [col for col in df_clean.columns if any(x in col for x in ['tid', 'aar', 'year', 'time'])]
    if time_cols:
        time_col = time_cols[0]
        logger.info(f"  Found time column: {time_col}")
        years = sorted(df_clean[time_col].unique())
        logger.info(f"  Years available: {years[0]} to {years[-1]}")

    # Convert numeric columns
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            try:
                # Try to convert to numeric (handling Danish format)
                df_clean[col] = pd.to_numeric(
                    df_clean[col].str.replace('.', '').str.replace(',', '.'),
                    errors='ignore'
                )
            except (AttributeError, ValueError):
                pass

    # Remove rows with all NaN values
    df_clean = df_clean.dropna(how='all')

    # Remove duplicate rows
    df_clean = df_clean.drop_duplicates()

    logger.info(f"  ✓ Cleaned data: {len(df_clean)} rows × {len(df_clean.columns)} columns")

    return df_clean


def create_summary_stats(df: pd.DataFrame, output_dir: Path):
    """
    Create summary statistics by district.

    Args:
        df: Cleaned DataFrame
        output_dir: Output directory
    """
    logger.info("Creating summary statistics...")

    # Find district column
    district_cols = [col for col in df.columns if 'bydel' in col or 'district' in col]
    if not district_cols:
        logger.warning("  No district column found, skipping summary")
        return

    district_col = district_cols[0]

    # Create summary
    summary = df.groupby(district_col).agg({
        col: ['sum', 'mean', 'count'] for col in df.select_dtypes(include=['number']).columns
    })

    # Flatten column names
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()

    # Save summary
    output_file = output_dir / f"demographics_summary_{datetime.now().strftime('%Y%m%d')}.csv"
    summary.to_csv(output_file, index=False)

    logger.info(f"  ✓ Saved summary to: {output_file}")

    # Display key statistics
    logger.info("\n" + "="*70)
    logger.info("SUMMARY STATISTICS BY DISTRICT")
    logger.info("="*70)

    # Find population column (antal = count/number in Danish)
    pop_cols = [col for col in summary.columns if 'antal' in col or 'population' in col or 'sum' in col]
    if pop_cols:
        pop_col = pop_cols[0]
        for _, row in summary.iterrows():
            district = row[district_col]
            value = row[pop_col]
            logger.info(f"  {district:30s}: {value:>10,.0f}")

    logger.info("="*70 + "\n")


def process_file(file_path: Path, output_dir: Path):
    """
    Process a single StatBank CSV file.

    Args:
        file_path: Path to CSV file
        output_dir: Output directory
    """
    try:
        # Load data
        df = load_statbank_csv(file_path)

        # Clean data
        df_clean = clean_statbank_data(df)

        # Save cleaned data
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{file_path.stem}_cleaned.csv"
        df_clean.to_csv(output_file, index=False)

        logger.info(f"  ✓ Saved cleaned data to: {output_file}")

        # Create summary stats
        create_summary_stats(df_clean, output_dir)

        # Save metadata
        metadata = {
            'source_file': file_path.name,
            'processing_date': datetime.now().isoformat(),
            'rows': len(df_clean),
            'columns': len(df_clean.columns),
            'column_names': df_clean.columns.tolist(),
        }

        metadata_file = output_dir / f"{file_path.stem}_metadata.txt"
        with open(metadata_file, 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")

        logger.info(f"  ✓ Saved metadata to: {metadata_file}")

        return df_clean

    except Exception as e:
        logger.error(f"  Failed to process {file_path}: {e}")
        raise


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'csv_files',
        type=Path,
        nargs='+',
        help='CSV file(s) to process'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('data/processed'),
        help='Output directory (default: data/processed)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        logger.info("\n" + "="*70)
        logger.info("COPENHAGEN STATBANK CSV PROCESSOR")
        logger.info("="*70)
        logger.info(f"Files to process: {len(args.csv_files)}")
        logger.info(f"Output directory: {args.output}")
        logger.info("="*70 + "\n")

        # Process each file
        processed_files = []
        for csv_file in args.csv_files:
            if not csv_file.exists():
                logger.warning(f"File not found: {csv_file}, skipping...")
                continue

            logger.info(f"\nProcessing: {csv_file}")
            logger.info("-" * 70)

            try:
                df = process_file(csv_file, args.output)
                processed_files.append((csv_file, df))
                logger.info("✓ Success!")

            except Exception as e:
                logger.error(f"✗ Failed: {e}")
                continue

        # Final summary
        logger.info("\n" + "="*70)
        logger.info("PROCESSING COMPLETE")
        logger.info("="*70)
        logger.info(f"Successfully processed: {len(processed_files)} files")
        logger.info(f"Output directory: {args.output}")
        logger.info("\nNext steps:")
        logger.info("  1. Review cleaned CSV files in data/processed/")
        logger.info("  2. Check summary statistics")
        logger.info("  3. Join with district spatial data (from bydele.gpkg)")
        logger.info("  4. Create demographic maps in QGIS")
        logger.info("="*70 + "\n")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
