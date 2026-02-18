"""
Process Raw Health Data into Analysis-Ready CSVs

Reads raw health data from multiple sources (Danskernes Sundhed survey CSVs,
StatBank DODA1 causes of death, StatBank FOD207 deaths by municipality),
translates Danish column names to English, combines same-structure files,
and saves to data/processed/.

Outputs:
- data/processed/health_survey_by_age.csv
- data/processed/health_survey_by_municipality.csv
- data/processed/health_causes_of_death.csv
- data/processed/health_deaths_by_municipality.csv

Usage:
    python scripts/process/process_health.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    HEALTH_CAUSES_OF_DEATH_OUTPUT,
    HEALTH_DANSKERNESSUNDHED_DIR,
    HEALTH_DEATHS_BY_MUNICIPALITY_OUTPUT,
    HEALTH_DODA1_FILE,
    HEALTH_FOD207_FILE,
    HEALTH_SURVEY_BY_AGE_OUTPUT,
    HEALTH_SURVEY_BY_MUNICIPALITY_OUTPUT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Danskernes Sundhed — indicator column mappings
# ---------------------------------------------------------------------------

# Per-age files: directory name -> (indicator_name, Danish column name for value)
PER_AGE_INDICATORS = {
    "physycal_activity": (
        "physical_activity",
        "Andel der ikke opfylder WHOs anbefaling for fysisk aktivitet",
    ),
    "obesity": (
        "obesity",
        "Andel med moderat eller svært overvægti",
    ),
    "stress": (
        "stress",
        "Andel med en høj score på stressskalaen",
    ),
    "self_rated": (
        "self_rated_health",
        "Andel med fremragende, vældig godt eller godt selvvurderet helbred",
    ),
    "longterm_illness": (
        "longterm_illness",
        "Andel der har en langvarig sygdom",
    ),
    "gp_contact": (
        "gp_contact",
        "Andel der har haft kontakt med egen læge inden for de seneste 12 måneder",
    ),
    "sedentary_leisure": (
        "sedentary_leisure",
        "Andel med stillesiddende fritidsaktivitet",
    ),
}

# Per-kommune files: directory name -> (indicator_name, value column, OR column)
PER_KOMMUNE_INDICATORS = {
    "physycal_activity": (
        "physical_activity",
        "Andel der ikke opfylder WHO's minimums anbefaling for fysisk aktivitet",
        "Opfylder ikke WHO's minimumsanbefaling for fysisk aktivitet. Køns- og aldersjusteret OR",
    ),
    "obesity": (
        "obesity",
        "Andel med moderat eller svær overvægt",
        "Moderat eller svær overvægt. Køns- og aldersjusteret OR",
    ),
    "stress": (
        "stress",
        "Andel med en høj score på stressskalaen",
        "Høj score på stressskalaen. Køns- og aldersjusteret OR",
    ),
    "self_rated": (
        "self_rated_health",
        "Andel med fremragende, vældig godt eller godt selvvurderet helbred",
        "Fremragende, vældig godt eller godt selvvurderet helbred. Køns- og aldersjusteret OR",
    ),
    "longterm_illness": (
        "longterm_illness",
        "Andel med langvarig sygdom",
        "Langvarig sygdom. Køns- og aldersjusteret OR",
    ),
    "gp_contact": (
        "gp_contact",
        "Andel med kontakt med egen læge inden for de seneste 12 måneder",
        "Kontakt med egen læge inden for de seneste 12 måneder. Køns- og aldersjusteret OR",
    ),
}

# Gender translation
GENDER_MAP = {
    "Mænd": "Male",
    "Kvinder": "Female",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def parse_pct(series):
    """Convert percentage strings like '36.6%' to floats."""
    return series.str.rstrip("%").astype(float)


def parse_respondent_count(series):
    """Convert respondent count strings like '1,160' to integers.

    Handles both string values with commas and already-numeric values.
    """
    return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce").astype("Int64")


def extract_year_from_filename(filename):
    """Extract year from Danskernes Sundhed filename patterns.

    Examples:
        sasExportLSWB_2023_perAge_capitalRegion.csv -> 2023
        sasExport6ZGN_2010.csv -> 2010
        sasExportYWG2_2021.csv -> 2021
    """
    parts = filename.stem.split("_")
    for part in parts:
        if part.isdigit() and len(part) == 4:
            return int(part)
    return None


# ---------------------------------------------------------------------------
# Process Danskernes Sundhed per-age files
# ---------------------------------------------------------------------------


def process_per_age_files():
    """Process all per-age survey CSVs into a single DataFrame.

    Combines files from all indicator directories, translates columns,
    drops total/summary rows, and returns a unified DataFrame.
    """
    logger.info("Processing Danskernes Sundhed per-age files...")
    frames = []

    for dir_name, (indicator_name, value_col) in PER_AGE_INDICATORS.items():
        indicator_dir = HEALTH_DANSKERNESSUNDHED_DIR / dir_name
        if not indicator_dir.exists():
            logger.warning("Directory not found: %s", indicator_dir)
            continue

        # Find per-age CSV files (contain 'perAge' or are sedentary files with year)
        csv_files = sorted(indicator_dir.glob("*.csv"))
        for csv_file in csv_files:
            # Skip per-kommune files
            if "perKomunne" in csv_file.name or "perKommune" in csv_file.name:
                continue

            year = extract_year_from_filename(csv_file)
            if year is None:
                logger.warning("Could not extract year from: %s", csv_file.name)
                continue

            logger.info("  Reading %s/%s (year=%d)", dir_name, csv_file.name, year)
            df = pd.read_csv(csv_file)

            # Find the value column (may have slight variations or curly quotes)
            def normalize_quotes(s):
                return s.replace("\u2019", "'").replace("\u2018", "'")

            matched_col = None
            for col in df.columns:
                col_norm = normalize_quotes(col)
                if col_norm == normalize_quotes(value_col) or col_norm.startswith(normalize_quotes(value_col)[:30]):
                    matched_col = col
                    break

            if matched_col is None:
                logger.warning(
                    "  Value column not found in %s. Columns: %s",
                    csv_file.name,
                    df.columns.tolist(),
                )
                continue

            # Drop total/summary rows (blank gender or age)
            df = df.dropna(subset=["Køn", "Alder"])
            df = df[df["Køn"].str.strip() != ""]
            df = df[df["Alder"].str.strip() != ""]

            # Build output DataFrame
            n = len(df)
            out = pd.DataFrame()
            out["indicator"] = [indicator_name] * n
            out["year"] = [year] * n
            out["gender"] = df["Køn"].map(GENDER_MAP).values
            out["age_group"] = (
                df["Alder"].str.replace(" år", "").str.strip().values
            )
            out["value_pct"] = parse_pct(df[matched_col]).values

            if "Antal svarpersoner" in df.columns:
                out["respondent_count"] = parse_respondent_count(
                    df["Antal svarpersoner"]
                ).values
            else:
                out["respondent_count"] = pd.NA

            frames.append(out)
            logger.info("    -> %d rows (after dropping totals)", len(out))

    if not frames:
        logger.error("No per-age files found!")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    logger.info("Combined per-age data: %d rows, %d indicators", len(result), result["indicator"].nunique())
    return result


# ---------------------------------------------------------------------------
# Process Danskernes Sundhed per-kommune files
# ---------------------------------------------------------------------------


def process_per_kommune_files():
    """Process all per-kommune survey CSVs into a single DataFrame.

    Combines files from all indicator directories, translates columns,
    and returns a unified DataFrame.
    """
    logger.info("Processing Danskernes Sundhed per-kommune files...")
    frames = []

    for dir_name, (indicator_name, value_col, or_col) in PER_KOMMUNE_INDICATORS.items():
        indicator_dir = HEALTH_DANSKERNESSUNDHED_DIR / dir_name
        if not indicator_dir.exists():
            logger.warning("Directory not found: %s", indicator_dir)
            continue

        # Find per-kommune CSV files
        csv_files = [
            f for f in sorted(indicator_dir.glob("*.csv"))
            if "perKomunne" in f.name or "perKommune" in f.name
        ]

        for csv_file in csv_files:
            year = extract_year_from_filename(csv_file)
            if year is None:
                year = 2021  # Default for per-kommune files

            logger.info("  Reading %s/%s (year=%d)", dir_name, csv_file.name, year)
            df = pd.read_csv(csv_file)

            # Find value and OR columns (normalize quotes for matching)
            def normalize_quotes(s):
                return s.replace("\u2019", "'").replace("\u2018", "'")

            matched_value_col = None
            matched_or_col = None
            for col in df.columns:
                col_norm = normalize_quotes(col)
                if col_norm == normalize_quotes(value_col) or col_norm.startswith(normalize_quotes(value_col)[:30]):
                    matched_value_col = col
                if col_norm == normalize_quotes(or_col) or col_norm.startswith(normalize_quotes(or_col)[:30]):
                    matched_or_col = col

            if matched_value_col is None:
                logger.warning(
                    "  Value column not found in %s. Columns: %s",
                    csv_file.name,
                    df.columns.tolist(),
                )
                continue

            # Build output DataFrame
            n = len(df)
            out = pd.DataFrame()
            out["indicator"] = [indicator_name] * n
            out["year"] = [year] * n
            out["municipality"] = df["Kommune"].values
            out["value_pct"] = parse_pct(df[matched_value_col]).values

            if matched_or_col is not None:
                out["odds_ratio"] = df[matched_or_col].astype(float).values
            else:
                out["odds_ratio"] = pd.NA

            frames.append(out)
            logger.info("    -> %d rows", len(out))

    if not frames:
        logger.error("No per-kommune files found!")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    logger.info(
        "Combined per-kommune data: %d rows, %d indicators",
        len(result),
        result["indicator"].nunique(),
    )
    return result


# ---------------------------------------------------------------------------
# Process StatBank DODA1 (causes of death)
# ---------------------------------------------------------------------------


def process_doda1():
    """Process StatBank DODA1 causes of death CSV.

    Translates Danish column headers to English.
    """
    logger.info("Processing StatBank DODA1 (causes of death)...")
    logger.info("  Reading %s", HEALTH_DODA1_FILE)

    df = pd.read_csv(HEALTH_DODA1_FILE, sep=";")
    logger.info("  Raw rows: %d", len(df))

    result = pd.DataFrame()
    result["cause"] = df["ÅRSAG"].values
    result["age"] = df["ALDER"].values
    result["gender"] = df["KØN"].values
    result["year"] = df["TID"].values
    result["deaths"] = df["INDHOLD"].values

    logger.info(
        "  Years: %d-%d, Causes: %d unique",
        result["year"].min(),
        result["year"].max(),
        result["cause"].nunique(),
    )
    return result


# ---------------------------------------------------------------------------
# Process StatBank FOD207 (deaths by municipality)
# ---------------------------------------------------------------------------


def process_fod207():
    """Process StatBank FOD207 deaths by municipality CSV.

    Handles UTF-8 BOM encoding and translates column headers.
    """
    logger.info("Processing StatBank FOD207 (deaths by municipality)...")
    logger.info("  Reading %s", HEALTH_FOD207_FILE)

    df = pd.read_csv(HEALTH_FOD207_FILE, sep=";", encoding="utf-8-sig")
    logger.info("  Raw rows: %d", len(df))

    # Find the area column (handles BOM/encoding variations)
    area_col = next(k for k in df.columns if "OMR" in k.upper())

    result = pd.DataFrame()
    result["area"] = df[area_col].values
    result["age"] = df["ALDER"].values
    result["gender"] = df["KØN"].values
    result["year"] = df["TID"].values
    result["deaths"] = df["INDHOLD"].values

    logger.info(
        "  Years: %d-%d, Areas: %s",
        result["year"].min(),
        result["year"].max(),
        result["area"].unique().tolist(),
    )
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def save_csv(df, output_path, description):
    """Save DataFrame to CSV and log file size."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    size_kb = output_path.stat().st_size / 1024
    logger.info("Saved %s to %s (%.1f KB, %d rows)", description, output_path, size_kb, len(df))


def main():
    logger.info("=" * 60)
    logger.info("HEALTH DATA PROCESSING")
    logger.info("=" * 60)

    # 1. Danskernes Sundhed per-age
    df_by_age = process_per_age_files()
    if not df_by_age.empty:
        save_csv(df_by_age, HEALTH_SURVEY_BY_AGE_OUTPUT, "survey by age")

    # 2. Danskernes Sundhed per-kommune
    df_by_municipality = process_per_kommune_files()
    if not df_by_municipality.empty:
        save_csv(df_by_municipality, HEALTH_SURVEY_BY_MUNICIPALITY_OUTPUT, "survey by municipality")

    # 3. StatBank DODA1
    df_doda1 = process_doda1()
    save_csv(df_doda1, HEALTH_CAUSES_OF_DEATH_OUTPUT, "causes of death")

    # 4. StatBank FOD207
    df_fod207 = process_fod207()
    save_csv(df_fod207, HEALTH_DEATHS_BY_MUNICIPALITY_OUTPUT, "deaths by municipality")

    # Summary
    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info("Outputs:")
    logger.info("  %s", HEALTH_SURVEY_BY_AGE_OUTPUT)
    logger.info("  %s", HEALTH_SURVEY_BY_MUNICIPALITY_OUTPUT)
    logger.info("  %s", HEALTH_CAUSES_OF_DEATH_OUTPUT)
    logger.info("  %s", HEALTH_DEATHS_BY_MUNICIPALITY_OUTPUT)


if __name__ == "__main__":
    main()
