# Population Typology Brief

Prompt for building a dwelling-to-population model that assigns realistic household compositions to residential buildings in Norrebro.

## Goal

Assign age-specific population estimates to each residential building, moving beyond naive area-proportional distribution. The model should account for dwelling typology — different apartment sizes attract different household types, which have distinct age profiles.

## Available Data

### Dwelling types + household sizes (`data/processed/norrebro_neighbourhoods_dwellings.csv`)

Per sub-neighbourhood breakdown of dwelling units by:
- **Dwelling type**: Multi-dwelling houses, Detached houses, Terraced/linked/semi-detached, Student hostels, Other
- **Household persons**: 0 (vacant), 1, 2, 3, 4, 5, 6+
- 5 sub-neighbourhoods x 5 dwelling types x 7 household sizes

This tells us *how many dwellings of each size exist* in each neighbourhood.

### Population by age group (`data/processed/norrebro_neighbourhoods_population.csv`)

Per sub-neighbourhood population in 20 five-year age bands (0-4, 5-9, ..., 90-94, 95+).
- 5 sub-neighbourhoods x 20 age groups = 100 rows
- Total population: 79,753

This tells us *how many people of each age live* in each neighbourhood.

### Building attributes (from `data/integrated/norrebro_buildings.gpkg`, `buildings` layer)

Each residential building has:
- `residential_area_m2` — total residential floor area
- `floors` — number of floors
- `use_description` — e.g., "Apartment building", "Terraced house"
- `gm_id` + `neighbourhood_name` — sub-neighbourhood link
- `total_area_m2`, `footprint_area_m2` — for deriving average unit size

## Approach Sketch

### 1. Estimate number of dwelling units per building

From `residential_area_m2` and typical unit sizes:
- Studio/1-bedroom: ~40-60 m²
- 2-bedroom: ~60-80 m²
- 3-bedroom: ~80-110 m²
- 4+ bedroom / family: ~110-150 m²

Use the dwelling type distribution from the CSV to calibrate: if a neighbourhood has 2,692 single-person dwellings in multi-dwelling houses, those are likely studios/1-beds. Match building stock to dwelling stock.

### 2. Map dwelling types to household compositions

Using the household persons distribution:
- 1-person dwellings: likely working-age singles (25-44) or elderly (65+)
- 2-person dwellings: couples (25-44) or elderly couples (65-79)
- 3-4 person dwellings: families with children (adults 30-49, children 0-14)
- 5-6 person dwellings: larger families (adults 30-54, children 0-19)

### 3. Distribute age-group population through typologies

Within each sub-neighbourhood:
1. Estimate total dwelling units from building stock
2. Assign dwelling type mix (from CSV) proportionally
3. Map each dwelling type to an age-group distribution
4. Calibrate so total population per age group per neighbourhood matches the CSV

### 4. Assign to buildings

Each building gets:
- Number of estimated dwelling units
- Household composition mix
- Age-specific population columns (can be aggregated to broader groups)

## Key Considerations

### WHO HEAT age breaks

The WHO HEAT tool uses specific age ranges for walking/cycling health benefit calculation. The population model should produce outputs compatible with these ranges. Key distinctions:
- Children (0-14): not independent walkers/cyclists
- Working age (15-64): primary active transport users, different walking speeds
- Elderly (65+): reduced walking speed (0.8-1.0 m/s vs 1.4 m/s baseline), higher health benefit per unit of activity

### Walking/cycling speed by age

Population age profiles directly affect accessibility analysis:
- Younger adults (20-44): ~1.4-1.5 m/s walking, ~15-18 km/h cycling
- Middle-aged (45-64): ~1.3-1.4 m/s walking
- Elderly (65-79): ~1.0-1.2 m/s walking
- Very elderly (80+): ~0.6-0.9 m/s walking

A building with mostly elderly residents has a smaller effective walkable catchment than one with young professionals.

### Student hostels

Norrebro has student housing — these have a distinctive age profile (18-30) and household size (1-2). The dwelling type "Student hostels" in the CSV captures this directly.

## Integration Point

Buildings already have `gm_id` + `residential_area_m2` + `use_description` from the integration step. The typology model adds population columns on top, saved either as additional columns in the buildings layer or as a separate lookup table keyed by building index.

## Output

Per residential building:
- `n_dwelling_units` — estimated number of units
- `pop_total` — total estimated population
- Age-group columns (granularity TBD — could be the 20 five-year bands, or broader groups aligned with HEAT/walking speed breaks)
- `dwelling_typology` — dominant dwelling type for the building
