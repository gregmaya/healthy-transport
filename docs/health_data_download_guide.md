# Health Data Download Guide

Step-by-step instructions for acquiring all health data sources for the Nørrebro healthy transport project. Sources 3 and 4 are automated via `scripts/download/download_health.py`. Sources 1, 2, and 5 require manual download.

---

## Source 1: Sundhedsdatabanken — Chronic Disease Register (MANUAL)

Municipality-level prevalence and incidence for chronic diseases (diabetes, COPD, asthma, osteoporosis, dementia, etc.) from 2010–2025.

### Steps

1. Go to: https://sundhedsdatabank.dk/sygdomme/kroniske-sygdomme-og-svaere-psykiske-lidelser
2. Look for the downloadable XLSX file titled **"Kroniske Sygdomme og Svære Psykiske Lidelser 2010-2025"** (published November 2025)
3. Download the XLSX file
4. Save it to: `data/raw/health/esundhed_kroniske_sygdomme_2010_2025.xlsx`

### What's inside

- **Diseases**: Type 1 diabetes, Type 2 diabetes, COPD (KOL), Asthma, Osteoporosis, Rheumatoid arthritis, Schizophrenia, Dementia
- **Measures**: Prevalence (existing cases) and Incidence (new cases per year)
- **Dimensions**: Age group, sex, municipality, year
- **Geographic level**: Municipality — filter for **København (0101)** for Copenhagen data

### Why we need it

Copenhagen-specific chronic disease burden. Diabetes, COPD, and asthma are directly linked to physical inactivity and urban environmental quality. Provides the "what" — which diseases affect Copenhagen residents — to motivate infrastructure changes.

---

## Source 2: Danskernes Sundhed — National Health Profile Survey (MANUAL)

Survey data on physical activity, BMI, self-rated health, and lifestyle factors at municipality level.

### Steps

1. Go to: https://www.danskernessundhed.dk/
2. Use the interactive SAS Visual Analytics viewer
3. For each indicator below, filter to **København** (Copenhagen municipality):

#### Indicators to extract

| Category | Indicator (Danish) | Indicator (English) | Look for |
| -------- | ------------------ | ------------------- | -------- |
| Sundhedsadfærd | Fysisk aktivitet | Physical activity | % meeting WHO 150 min/week recommendation |
| Sundhedsadfærd | Stillesiddende fritidsaktivitet | Sedentary leisure | % with sedentary leisure activity |
| Sundhedsadfærd | Overvægt / Svær overvægt | Overweight / Obesity | % with BMI >= 25 / BMI >= 30 |
| Helbred og trivsel | Selvvurderet helbred | Self-rated health | % reporting good/very good health |
| Helbred og trivsel | Stress | Stress | % with high stress level |
| Sygelighed | Langvarig sygdom | Long-term illness | % with long-term illness |
| Kontakt til egen læge | Kontakt til praktiserende læge | GP contact | Annual contact rate |

4. For each indicator, download **two views**:
   - **2021 per kommune**: Filter to Capital Region municipalities. This gives Copenhagen vs. surrounding municipalities for context.
   - **2023 per age (Capital Region)**: Filter by sex and age group within the Capital Region. This gives age-differentiated data.
5. Export each view as CSV using the SAS Visual Analytics export function
6. Available survey years: **2010, 2013, 2017, 2021, 2023** (2021 is the most recent with per-kommune data; 2023 has per-age breakdowns)
7. Save to: `data/raw/health/danskernessundhed/<indicator>/` (one subdirectory per indicator)

### Actual file structure (as downloaded)

```
data/raw/health/danskernessundhed/
├── physycal_activity/
│   ├── sasExportERMM_2021_perKomunne.csv
│   └── sasExport24O6_2023_perAge_capitalRegion.csv  ⚠️ DATA ISSUE — see below
├── obesity/
│   ├── sasExport4FRF_2021_perKomunne.csv
│   └── sasExport153R_2023_perAge_capitalRegion.csv
├── self_rated/
│   ├── sasExportXI08_2021_perKomunne.csv
│   └── sasExport24BY_2023_perAge_capitalRegion.csv
├── stress/
│   ├── sasExportGYQQ_2021_perKomunne.csv
│   └── sasExportTVLE_2023_perAge_capitalRegion.csv
├── longterm_illness/
│   ├── sasExportYEA6_2021_perKomunne.csv
│   └── sasExportD0BC__2023_perAge_capitalRegion.csv
├── gp_contact/
│   ├── sasExport9ODV_2021_perKomunne.csv
│   └── sasExportL5U0_2023_perAge_capitalRegion.csv
└── sedentary_leisure/
    ├── sasExport6ZGN_2010.csv
    ├── sasExportWGTJ_2013.csv
    └── sasExportYWG2_2021.csv
```

### Known data issue

The **physical activity per-age file** (`sasExport24O6_2023_perAge_capitalRegion.csv`) contains broken data — values of 100%/200% with 0-1 respondents per cell. This suggests the data was downloaded at too narrow a geographic filter. **This file needs to be re-downloaded** from Danskernes Sundhed with the filter set to the Capital Region level (Region Hovedstaden), matching the pattern of the other per-age files which have 90-310 respondents per cell.

### CSV format (per-kommune files)

```csv
"Kommune","Andel der ikke opfylder WHO's minimums anbefaling for fysisk aktivitet","Opfylder ikke WHO's minimumsanbefaling for fysisk aktivitet. Køns- og aldersjusteret OR"
"København","50.3%","0.74"
```

### CSV format (per-age files)

```csv
"Køn","Alder","Andel med moderat eller svært overvægti","Antal svarpersoner"
"Mænd","16-24 år","29.8%","90"
```

### Why we need it

Physical activity levels and lifestyle factors at Copenhagen level. This connects transport infrastructure (walking/cycling accessibility) to health behaviours. The age breakdowns show which populations are most/least active — critical for the design framework.

---

## Source 3: StatBank Denmark — Causes of Death, DODA1 (AUTOMATED)

National-level deaths by cause, age, and sex. Downloaded automatically by `scripts/download/download_health.py`.

### What the script downloads

- **Table**: DODA1
- **API**: `https://api.statbank.dk/v1/data`
- **Variables**: All 25 cause-of-death categories, all age groups, both sexes, all years (2007–2022)
- **Format**: CSV (semicolon-separated)
- **Saved to**: `data/raw/health/statbank_doda1_causes_of_death.csv`

### Key cause-of-death categories

| Code | Category (English) |
| ---- | ------------------ |
| A01 | Infectious or parasitic diseases |
| A02 | Cancer |
| A04 | Endocrine, nutritional and metabolic diseases (incl. diabetes) |
| A07 | Heart diseases |
| A08 | Other diseases of the circulatory system |
| A09 | Respiratory diseases |
| A18 | Accidents |
| A19 | Suicide and self-harm |

### Why we need it

Top-down narrative framing: "Heart disease and diabetes are among the leading causes of death in Denmark. Both are strongly linked to physical inactivity, which can be addressed through urban design that promotes walking and cycling."

---

## Source 4: StatBank Denmark — Deaths by Municipality, FOD207 (AUTOMATED)

Deaths by municipality, age, and sex. Downloaded automatically by `scripts/download/download_health.py`.

### What the script downloads

- **Table**: FOD207
- **API**: `https://api.statbank.dk/v1/data`
- **Variables**: Copenhagen municipality (101), Region Hovedstaden (084), all of Denmark (000), all age groups, both sexes, all years (2006–2025)
- **Format**: CSV (semicolon-separated)
- **Saved to**: `data/raw/health/statbank_fod207_deaths_by_region.csv`

### Why we need it

Compare Copenhagen mortality to national and regional patterns by age. Provides context for the chronic disease data — do Copenhageners die at different ages or rates than the national average?

---

## Source 5: WHO HEAT Tool — Health Economic Assessment (MANUAL)

Framework for calculating the economic value of health benefits from walking and cycling infrastructure improvements.

### Step A: Download the methodology guide

1. Go to: https://www.who.int/europe/publications/i/item/9789289058377
2. Download the PDF: **"Health economic assessment tool (HEAT) for walking and for cycling. Methods and user guide on physical activity, air pollution, road fatalities and carbon impact assessments: 2024 update"** (128 pages)
3. Save to: `data/raw/health/WHO_HEAT_user_guide_2024.pdf`

### Step B: Explore the web tool

1. Go to: https://www.heatwalkingcycling.org
2. Create an assessment for Copenhagen / Nørrebro
3. The tool asks for these inputs (defaults are provided for most):

| Input | Description | Where to find for Nørrebro |
| ----- | ----------- | -------------------------- |
| Population | Number of people in study area | Our demographics data: `data/raw/demographics/` |
| Current walking/cycling level | Trips per day, distance, or modal share | Can estimate from our pedestrian network + transport data |
| Mortality rate | All-cause mortality per 100,000 | StatBank FOD207 data (Source 4 above) |
| Air pollution (PM2.5) | Annual mean concentration | European Environment Agency or local monitoring |
| Road fatality rate | Fatalities per billion km walked/cycled | Danish Road Directorate (Vejdirektoratet) statistics |

### Step C: Gather HEAT-specific local data

These additional data points would strengthen a HEAT assessment:

1. **Modal share data for Copenhagen**: What % of trips are by walking, cycling, public transport, car?
   - Source: Copenhagen Municipality traffic counts or Danish Transport Authority (Transportministeriet)
   - Check: https://www.kk.dk/mobilitetsredegoerelse (Copenhagen Mobility Report)

2. **Air quality (PM2.5)**: Annual mean particulate matter concentration
   - Source: Danish Centre for Environment and Energy (DCE) at Aarhus University
   - Or: European Environment Agency air quality data (https://www.eea.europa.eu/en/topics/in-depth/air-quality)

3. **Road fatality statistics**: Pedestrian and cyclist fatalities
   - Source: Vejdirektoratet (Danish Road Directorate) accident statistics
   - Check: https://www.vejdirektoratet.dk/statistik

### Why we need it

The HEAT tool is the bridge between infrastructure and health economics. It answers: "If we improve walking/cycling infrastructure in Nørrebro, leading to X more minutes of walking per person per day, what is the economic value of prevented premature deaths?" This is the actionable output that gives designers a quantified reason to prioritise active transport infrastructure.

---

## Summary Checklist

After completing all downloads, you should have:

```
data/raw/health/
├── esundhed_kroniske_sygdomme_2010_2025.xlsx    ← Manual (Source 1)
├── copenhagen_sundhedsprofil_indicators.csv      ← Manual (Source 2)
├── statbank_doda1_causes_of_death.csv            ← Automated (Source 3)
├── statbank_fod207_deaths_by_municipality.csv    ← Automated (Source 4)
└── WHO_HEAT_user_guide_2024.pdf                  ← Manual (Source 5)
```

Run `python scripts/download/download_health.py` to:
- Automatically download Sources 3 and 4
- Verify that Sources 1, 2, and 5 exist (prints status for each)
