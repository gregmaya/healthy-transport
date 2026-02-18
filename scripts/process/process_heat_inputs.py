"""
Compute WHO HEAT Tool Input Parameters for Nørrebro

Assembles all input parameters needed for a single-case assessment in the
WHO HEAT web tool (heatwalkingcycling.org). Reads from existing project
datasets (population CSV, FOD207 mortality CSV) and supplements with
Copenhagen population data from the StatBank Denmark API (FOLK1A table).

Outputs:
- Console summary of all HEAT parameters
- data/processed/heat_inputs.json (machine-readable reference)

Usage:
    python scripts/process/process_heat_inputs.py
"""

import csv
import json
import logging
import sys
from io import StringIO
from pathlib import Path

import requests

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    HEALTH_FOD207_FILE,
    HEAT_INPUTS_OUTPUT,
    PROCESSED_DATA_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STATBANK_API_URL = "https://api.statbank.dk/v1/data"

# Nørrebro population CSV (cleaned demographics data)
NORREBRO_POPULATION_FILE = PROCESSED_DATA_DIR / "norrebro_neighbourhoods_population.csv"

# HEAT age ranges
WALKING_AGE_RANGE = (20, 74)  # HEAT walking assessment: 20-74 years
CYCLING_AGE_RANGE = (20, 64)  # HEAT cycling assessment: 20-64 years

# External parameters (from research — see docs/heat_assessment_inputs.md)
COPENHAGEN_PM25 = 9.8  # µg/m³, IQAir/EEA 2024 estimate
CYCLING_FATALITY_RATE = 15.9  # per billion km, ITF/OECD for Denmark
MODAL_SHARE_WALKING = 0.21  # DTU Transport Survey 2018, Copenhagen
MODAL_SHARE_CYCLING = 0.28  # DTU Transport Survey 2018, Copenhagen


# ---------------------------------------------------------------------------
# Nørrebro population from project data
# ---------------------------------------------------------------------------


def parse_age_group(age_str):
    """Extract the lower age bound from age group string like '20-24 years'.

    Returns (lower_bound, upper_bound) as integers.
    """
    age_str = age_str.strip()
    if "+" in age_str:
        # e.g. "95+ years"
        lower = int(age_str.split("+")[0])
        return (lower, 120)
    parts = age_str.replace(" years", "").split("-")
    if len(parts) == 2:
        return (int(parts[0]), int(parts[1]))
    return None


def calculate_norrebro_population():
    """Calculate Nørrebro population totals from neighbourhood CSV.

    Returns dict with total, aged_20_74, aged_20_64 populations.
    """
    logger.info("Reading Nørrebro population from %s", NORREBRO_POPULATION_FILE)

    total = 0
    aged_20_74 = 0
    aged_20_64 = 0

    with open(NORREBRO_POPULATION_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            people = int(row["people"])
            total += people

            age_range = parse_age_group(row["ages"])
            if age_range is None:
                continue

            lower, upper = age_range

            # Check overlap with 20-74 range
            if upper >= 20 and lower <= 74:
                aged_20_74 += people

            # Check overlap with 20-64 range
            if upper >= 20 and lower <= 64:
                aged_20_64 += people

    logger.info("Nørrebro total population: %d", total)
    logger.info("Nørrebro population aged 20-74 (walking): %d", aged_20_74)
    logger.info("Nørrebro population aged 20-64 (cycling): %d", aged_20_64)

    return {
        "total": total,
        "aged_20_74": aged_20_74,
        "aged_20_64": aged_20_64,
    }


# ---------------------------------------------------------------------------
# Copenhagen mortality rate from FOD207
# ---------------------------------------------------------------------------


def calculate_copenhagen_mortality():
    """Calculate Copenhagen all-cause mortality rate from FOD207 data.

    Uses the most recent complete year of data. Sums deaths for ages 20-74
    across both sexes.

    Returns dict with deaths, year, and rate per 100,000.
    """
    logger.info("Reading FOD207 deaths data from %s", HEALTH_FOD207_FILE)

    # Parse FOD207 CSV (semicolon-separated)
    deaths_by_year = {}  # year -> total deaths aged 20-74

    with open(HEALTH_FOD207_FILE, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # Find the area column (handles BOM/encoding variations)
            area_col = next(k for k in row if "OMR" in k.upper())
            if row[area_col] != "Copenhagen":
                continue

            age_str = row["ALDER"]
            if age_str == "Age, total":
                continue

            # Parse "N years" format
            try:
                age = int(age_str.replace(" years", ""))
            except ValueError:
                continue

            if age < 20 or age > 74:
                continue

            year = int(row["TID"])
            deaths = int(row["INDHOLD"]) if row["INDHOLD"] else 0

            if year not in deaths_by_year:
                deaths_by_year[year] = 0
            deaths_by_year[year] += deaths

    # Use most recent complete year (skip current year which may be partial)
    available_years = sorted(deaths_by_year.keys())
    logger.info("FOD207 years with Copenhagen data: %s", available_years)

    # Use 2023 as most recent likely-complete year (2024/2025 may be partial)
    recent_year = max(y for y in available_years if y <= 2023)
    deaths_20_74 = deaths_by_year[recent_year]
    logger.info(
        "Copenhagen deaths aged 20-74 in %d: %d", recent_year, deaths_20_74
    )

    return {
        "year": recent_year,
        "deaths_20_74": deaths_20_74,
    }


# ---------------------------------------------------------------------------
# Copenhagen population from StatBank API (FOLK1A)
# ---------------------------------------------------------------------------


def download_copenhagen_population():
    """Download Copenhagen population by age from StatBank FOLK1A.

    Returns total Copenhagen population and population aged 20-74.
    """
    logger.info("Downloading Copenhagen population from StatBank FOLK1A...")

    payload = {
        "table": "FOLK1A",
        "format": "CSV",
        "lang": "en",
        "variables": [
            {"code": "OMRÅDE", "values": ["101"]},  # Copenhagen municipality
            {"code": "ALDER", "values": ["*"]},  # All ages
            {"code": "KØN", "values": ["TOT"]},  # Total (both sexes)
            {"code": "Tid", "values": ["*"]},  # All quarters
        ],
    }

    response = requests.post(STATBANK_API_URL, json=payload, timeout=120)
    response.raise_for_status()

    # Parse CSV response
    reader = csv.DictReader(StringIO(response.text), delimiter=";")
    rows = list(reader)

    # Find the most recent quarter
    quarters = set()
    for row in rows:
        quarters.add(row["TID"])
    most_recent = sorted(quarters)[-1]
    logger.info("Most recent population quarter: %s", most_recent)

    total_pop = 0
    pop_20_74 = 0
    pop_20_64 = 0

    for row in rows:
        if row["TID"] != most_recent:
            continue

        age_str = row["ALDER"]
        people = int(row["INDHOLD"]) if row["INDHOLD"] else 0

        if age_str == "Age, total":
            total_pop = people
            continue

        # Parse "N years" format
        try:
            age = int(age_str.replace(" years", ""))
        except ValueError:
            continue

        if 20 <= age <= 74:
            pop_20_74 += people
        if 20 <= age <= 64:
            pop_20_64 += people

    logger.info("Copenhagen total population (%s): %d", most_recent, total_pop)
    logger.info("Copenhagen population aged 20-74: %d", pop_20_74)
    logger.info("Copenhagen population aged 20-64: %d", pop_20_64)

    return {
        "quarter": most_recent,
        "total": total_pop,
        "aged_20_74": pop_20_74,
        "aged_20_64": pop_20_64,
    }


# ---------------------------------------------------------------------------
# Assemble HEAT inputs
# ---------------------------------------------------------------------------


def assemble_heat_inputs():
    """Assemble all HEAT input parameters."""

    # 1. Nørrebro population
    norrebro_pop = calculate_norrebro_population()

    # 2. Copenhagen mortality
    mortality = calculate_copenhagen_mortality()

    # 3. Copenhagen population (for mortality rate denominator)
    cph_pop = download_copenhagen_population()

    # Calculate mortality rate per 100,000
    if cph_pop["aged_20_74"] > 0:
        mortality_rate = (
            mortality["deaths_20_74"] / cph_pop["aged_20_74"]
        ) * 100_000
    else:
        mortality_rate = 500  # HEAT default for Denmark
        logger.warning("Could not calculate mortality rate, using HEAT default")

    logger.info(
        "Copenhagen mortality rate (20-74): %.1f per 100,000 (year %d)",
        mortality_rate,
        mortality["year"],
    )

    # Assemble all parameters
    heat_inputs = {
        "assessment_type": "single-case",
        "geographic_level": "sub-city (Nørrebro, Copenhagen)",
        "population": {
            "study_area": "Nørrebro, Copenhagen",
            "total": norrebro_pop["total"],
            "aged_20_74_walking": norrebro_pop["aged_20_74"],
            "aged_20_64_cycling": norrebro_pop["aged_20_64"],
            "source": "norrebro_neighbourhoods_population.csv (2025Q4)",
        },
        "mortality": {
            "rate_per_100k": round(mortality_rate, 1),
            "deaths_20_74": mortality["deaths_20_74"],
            "denominator_pop_20_74": cph_pop["aged_20_74"],
            "year": mortality["year"],
            "geography": "Copenhagen municipality (proxy for Nørrebro)",
            "heat_default_denmark": 500,
            "source": "Calculated from StatBank FOD207 + FOLK1A",
        },
        "modal_share": {
            "walking": MODAL_SHARE_WALKING,
            "cycling": MODAL_SHARE_CYCLING,
            "car": 0.32,
            "public_transport": 0.19,
            "year": 2018,
            "source": "DTU Transport Survey 2018 (Copenhagen municipality)",
            "note": "Nørrebro-specific data not available; Copenhagen average used as proxy",
        },
        "air_pollution": {
            "pm25_annual_mean_ugm3": COPENHAGEN_PM25,
            "source": "IQAir/EEA 2024 estimate for Copenhagen",
        },
        "road_crashes": {
            "cycling_fatality_per_billion_km": CYCLING_FATALITY_RATE,
            "walking_fatality": "Use HEAT Denmark default",
            "source": "ITF/OECD exposure-adjusted data for Denmark",
        },
        "heat_background_values": {
            "walking": {
                "relative_risk": 0.89,
                "reference_duration_min_per_week": 168,
                "benefits_cap_percent": 30,
                "age_range": "20-74",
            },
            "cycling": {
                "relative_risk": 0.90,
                "reference_duration_min_per_week": 100,
                "benefits_cap_percent": 45,
                "age_range": "20-64",
            },
        },
    }

    return heat_inputs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("WHO HEAT TOOL — INPUT PARAMETER COMPUTATION")
    logger.info("=" * 60)

    heat_inputs = assemble_heat_inputs()

    # Save to JSON
    HEAT_INPUTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(HEAT_INPUTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(heat_inputs, f, indent=2, ensure_ascii=False)

    size_kb = HEAT_INPUTS_OUTPUT.stat().st_size / 1024
    logger.info("Saved HEAT inputs to %s (%.1f KB)", HEAT_INPUTS_OUTPUT, size_kb)

    # Print summary
    logger.info("=" * 60)
    logger.info("HEAT INPUT SUMMARY")
    logger.info("=" * 60)

    pop = heat_inputs["population"]
    logger.info("Population (Nørrebro):")
    logger.info("  Total: %d", pop["total"])
    logger.info("  Aged 20-74 (walking): %d", pop["aged_20_74_walking"])
    logger.info("  Aged 20-64 (cycling): %d", pop["aged_20_64_cycling"])

    mort = heat_inputs["mortality"]
    logger.info("Mortality (Copenhagen, %d):", mort["year"])
    logger.info("  Rate: %.1f per 100,000 (ages 20-74)", mort["rate_per_100k"])
    logger.info("  HEAT default for Denmark: %d", mort["heat_default_denmark"])

    ms = heat_inputs["modal_share"]
    logger.info("Modal share (Copenhagen %d):", ms["year"])
    logger.info("  Walking: %.0f%%", ms["walking"] * 100)
    logger.info("  Cycling: %.0f%%", ms["cycling"] * 100)

    ap = heat_inputs["air_pollution"]
    logger.info("Air pollution: PM2.5 = %.1f µg/m³", ap["pm25_annual_mean_ugm3"])

    rc = heat_inputs["road_crashes"]
    logger.info(
        "Road crashes: cycling = %.1f fatalities/billion km",
        rc["cycling_fatality_per_billion_km"],
    )

    logger.info("=" * 60)
    logger.info("COMPUTATION COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
