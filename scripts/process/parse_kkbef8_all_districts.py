"""
Parse KKBEF8 Excel into a tidy population CSV covering all 67 Copenhagen sub-districts.

The raw 2025_KKBEF8.xlsx sheet has a hierarchical layout: age group is in col 2,
district name in col 3, count in col 4. This script:

  1. Reads that sheet and extracts all (age_group, district_name, count) rows.
  2. Maps each district name to its kvarternr (numeric sub-district code) via a
     normalised-string lookup + a small hardcoded fallback for tricky cases.
  3. Saves the result to data/processed/all_districts_population.csv with columns:
        gm_id (kvarternr), period, ages, kvarternavn, people

This CSV is a superset of norrebro_neighbourhoods_population.csv (which only
covers kvarternr 20401–20405). The integration script uses it to give buffer-zone
buildings real population counts.

Usage:
    python scripts/process/parse_kkbef8_all_districts.py
"""

import logging
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
KKBEF8_XLSX = PROJECT_ROOT / "data" / "raw" / "demographics" / "2025_KKBEF8.xlsx"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "all_districts_population.csv"

# ---------------------------------------------------------------------------
# kvarternr → canonical WFS name (from copenhagen_kvartergrænser.gpkg)
# ---------------------------------------------------------------------------
KVARTERNR_TO_NAME = {
    20101: "Middelalderbyen",
    20102: "Metropolzonen",
    20103: "Nansensgade-Kvarteret",
    20104: "Øster Farimagsgade-kvarteret",
    20105: "Østerport",
    20106: "Frederiksstaden",
    20107: "Gammelholm og Nyhavn",
    20201: "Christianshavn Neden Vandet",
    20202: "Christianshavn Oven Vandet",
    20203: "Holmen og Refshaleøen",
    20301: "Nord/Komponistkvarteret",
    20302: "Svanemøllen Syd/Øst",
    20303: "Århusgade Nord",
    20304: "Århusgade Syd",
    20305: "Rosenvænget",
    20306: "Ny Ryvang",
    20307: "Østerbro Nord",
    20308: "Nordhavn",
    20309: "Lyngbyvej Vest",
    20310: "Lyngbyvej Øst/Klimakvarteret",
    20311: "Fælled",
    20401: "Blågårdskvarteret/Assistens/Rantzausgade",
    20402: "Guldbergskvarteret/Panum/Ravnsborggade",
    20403: "Stefansgade/Nørrebroparken/Lundtoftegade",
    20404: "Mimersgade-kvarteret",
    20405: "Haraldsgade-kvarteret",
    20501: "Vesterbro vest",
    20502: "Vesterbro central",
    20503: "Vesterbro øst",
    20504: "Vesterbro syd",
    20601: "Bavnehøj",
    20602: "Gl. Sydhavn",
    20603: "Holmene",
    20701: "Gl. Valby",
    20702: "Valby syd",
    20703: "Ålholm",
    20704: "Valby sydvest",
    20705: "Vigerslev",
    20801: "Jyllingevej Kvarter",
    20802: "Jernbane Allé Kvarter",
    20803: "Sallingvej Kvarter",
    20804: "Grøndals Park Kvarter",
    20901: "Husum",
    20902: "Husum Nord",
    20903: "Tingbjerg",
    20904: "Brønshøj",
    20905: "Bellahøj",
    21001: "Emdrup",
    21002: "Ryparken-Lundehus",
    21003: "Bispebjerg",
    21004: "Utterslev",
    21005: "Nordvest",
    21101: "Amagerbro øst",
    21102: "Sundbyøster",
    21103: "Villakvartererne",
    21104: "Nordøstamager",
    21201: "Amagerbro vest",
    21202: "Bryggen Syd",
    21203: "Faste Batteri",
    21204: "Gamle Bryggen",
    21205: "Grønjordssøen (Ørestad Nord, Vejlands Kvarter)",
    21206: "Kolonihavekvarteret",
    21207: "Sundbyvester",
    21208: "Sundholmsvejs kvarteret",
    21209: "Urbanplanen",
    21210: "Ørestad City",
    21211: "Ørestad Syd",
}

# ---------------------------------------------------------------------------
# Hardcoded fallback for Excel names that don't auto-match after normalisation
# ---------------------------------------------------------------------------
EXCEL_NAME_OVERRIDES = {
    # Excel name (exact, as read from file)                           → kvarternr

    "Bispebjerg- Ryparken-Lundehus": 21002,          # missing space before hyphen
    "Christianshavn - Neden Vandet": 20201,
    "Christianshavn - Oven Vandet": 20202,
    "N\u00afrrebro - Mimersgade-kvarteret/ N\u00afrrebro St.": 20404,  # extra suffix
    "Valby - Syd": 20702,
    "Vesterbro - Central": 20502,
    "Vesterbro - Syd": 20504,
    "Vesterbro - Vest": 20501,
    "Vesterbro - \u00ffst": 20503,   # mojibake for Vesterbro - Øst
    "\u00ffsterbro - Nord": 20307,   # mojibake for Østerbro - Nord
}

# Names to skip (not real districts)
SKIP_NAMES = {" ", "Neighborhood - Unlocated"}


def _normalise(s: str) -> str:
    """Strip district prefix, lowercase, remove punctuation."""
    s = str(s).lower().strip()
    if " - " in s:
        s = s.split(" - ", 1)[1]
    return re.sub(r"[^a-z0-9]", "", s)


def _build_lookup() -> dict[str, int]:
    norm = {}
    for nr, name in KVARTERNR_TO_NAME.items():
        key = _normalise(name)
        norm[key] = nr
    return norm


def parse_excel(path: Path) -> pd.DataFrame:
    """
    Read the raw KKBEF8 sheet and return a tidy DataFrame with columns:
        age_group (str), excel_name (str), people (int)
    """
    raw = pd.read_excel(path, sheet_name=0, header=None)

    # Extract period from row 2, col 4 (e.g. "2025Q4")
    period = str(raw.iloc[2, 4]).strip()
    log.info("Period from Excel: %s", period)

    rows = []
    current_age = None

    for _, row in raw.iterrows():
        age_val = row.iloc[2]
        name_val = row.iloc[3]
        count_val = row.iloc[4]

        # Update current age group when a new one appears in col 2
        if pd.notna(age_val) and str(age_val).strip() not in ("", " "):
            current_age = str(age_val).strip()

        # A data row has a name in col 3 and a numeric count in col 4
        if (
            current_age is not None
            and pd.notna(name_val)
            and str(name_val).strip() not in ("", " ")
            and pd.notna(count_val)
        ):
            try:
                count = int(count_val)
            except (ValueError, TypeError):
                continue
            rows.append({
                "period": period,
                "ages": current_age,
                "excel_name": str(name_val).strip(),
                "people": count,
            })

    df = pd.DataFrame(rows)
    log.info("Extracted %d raw rows (%d age groups)", len(df), df["ages"].nunique())
    return df


def map_to_kvarternr(df: pd.DataFrame) -> pd.DataFrame:
    """Add gm_id (kvarternr) column by matching excel_name to the lookup."""
    lookup = _build_lookup()

    # Pre-build reverse lookup from raw Excel name (for overrides)
    override_map = {}
    for raw_name, nr in EXCEL_NAME_OVERRIDES.items():
        override_map[raw_name] = nr

    results = []
    unmatched = set()

    for excel_name in df["excel_name"].unique():
        if excel_name in SKIP_NAMES:
            continue

        # 1. Try exact override match
        if excel_name in override_map:
            results.append((excel_name, override_map[excel_name]))
            continue

        # 2. Try normalised match
        key = _normalise(excel_name)
        if key in lookup:
            results.append((excel_name, lookup[key]))
            continue

        # 3. Substring fallback for mojibake names — match by unique keyword
        #    after stripping the district prefix. "Vejlandskvarter" is unique to 21205.
        if "Vejlandskvarter" in excel_name:
            results.append((excel_name, 21205))
            continue

        unmatched.add(excel_name)

    if unmatched:
        log.warning("Could not match %d Excel names:", len(unmatched))
        for name in sorted(unmatched):
            log.warning("  UNMATCHED: %r", name)

    name_to_nr = dict(results)
    df = df[~df["excel_name"].isin(SKIP_NAMES)].copy()
    df["gm_id"] = df["excel_name"].map(name_to_nr)

    n_null = df["gm_id"].isna().sum()
    if n_null > 0:
        log.warning("%d rows dropped (no kvarternr match)", n_null)
        df = df[df["gm_id"].notna()].copy()

    df["gm_id"] = df["gm_id"].astype(int)
    return df


def main() -> None:
    log.info("Reading %s", KKBEF8_XLSX)
    df = parse_excel(KKBEF8_XLSX)

    log.info("Mapping Excel district names → kvarternr ...")
    df = map_to_kvarternr(df)

    # Add canonical name from lookup
    df["kvarternavn"] = df["gm_id"].map(KVARTERNR_TO_NAME)

    # Reorder columns to match existing norrebro CSV convention
    df = df[["gm_id", "period", "ages", "kvarternavn", "people"]].sort_values(
        ["gm_id", "ages"]
    )

    n_districts = df["gm_id"].nunique()
    n_age_groups = df["ages"].nunique()
    log.info("Result: %d rows, %d sub-districts, %d age groups", len(df), n_districts, n_age_groups)

    # Sanity: check total population for Nørrebro matches the existing CSV
    norrebro_ids = {20401, 20402, 20403, 20404, 20405}
    norrebro_total = df[df["gm_id"].isin(norrebro_ids)]["people"].sum()
    log.info("Nørrebro total across all age groups: %d (expect ~1.3M across all bands)", norrebro_total)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    log.info("Saved → %s (%.1f KB)", OUTPUT_CSV, OUTPUT_CSV.stat().st_size / 1024)


if __name__ == "__main__":
    main()
