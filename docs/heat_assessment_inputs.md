# WHO HEAT Tool — Input Parameters for Nørrebro

Ready-to-use reference for entering data into the HEAT web tool at [heatwalkingcycling.org](https://www.heatwalkingcycling.org). All values computed by `scripts/process/process_heat_inputs.py` and saved to `data/processed/heat_inputs.json`.

---

## Assessment Setup

| Field | Value |
| ----- | ----- |
| Assessment type | Single-case (current levels) |
| Active mode | Walking **and** Cycling (run as separate assessments) |
| Country | Denmark |
| City/region | Copenhagen |
| Geographic level | Sub-city |
| Study area name | Nørrebro, Copenhagen |

---

## Step 1: Travel Data Inputs

### Walking Assessment

| Field | Value | Confidence | Source |
| ----- | ----- | ---------- | ------ |
| Modal share | **21%** | Medium | DTU Transport Survey 2018 (Copenhagen municipality-wide) |
| Or: duration per person | 168 min/week is the HEAT reference | — | HEAT default for full benefit |

### Cycling Assessment

| Field | Value | Confidence | Source |
| ----- | ----- | ---------- | ------ |
| Modal share | **28%** | Medium | DTU Transport Survey 2018 (Copenhagen municipality-wide) |
| Or: duration per person | 100 min/week is the HEAT reference | — | HEAT default for full benefit |

**Note on modal share**: These are Copenhagen municipality averages. Nørrebro-specific modal share is not publicly available. Given Nørrebro's high density and young demographics, actual walking/cycling shares are likely **higher** than the Copenhagen average. The 2022 Copenhagen Bicycle Account reports 49% of work/education trips by bike citywide.

---

## Step 2: Population Data

| Field | Value | Source |
| ----- | ----- | ------ |
| Total population | **79,753** | `norrebro_neighbourhoods_population.csv` (2025Q4, Statistics Denmark KKBEF8) |
| Population aged 20-74 (walking) | **63,529** | Calculated from same CSV |
| Population aged 20-64 (cycling) | **59,605** | Calculated from same CSV |

### Age distribution context

Nørrebro is a young neighbourhood — the 25-34 age group alone accounts for ~13,900 people (17% of total). The 20-44 range makes up ~45,300 (57% of total). This skews significantly younger than the Copenhagen or national average, which affects the mortality rate interpretation.

---

## Step 3: Mortality Rate

| Field | Value | Source |
| ----- | ----- | ------ |
| All-cause mortality rate (20-74) | **278.7 per 100,000/year** | Calculated: FOD207 deaths (1,438 in 2023) / FOLK1A population (515,913 aged 20-74) |
| HEAT default for Denmark | 500 per 100,000/year | Built into HEAT tool |

**Use 278.7** (the Copenhagen-specific rate) rather than the HEAT Denmark default of 500. The difference is significant and reflects Copenhagen's younger, urban population. Using the national default would overestimate mortality benefits by ~80%.

### Calculation details

- **Numerator**: 1,438 deaths in Copenhagen municipality, ages 20-74, year 2023 (StatBank FOD207)
- **Denominator**: 515,913 people aged 20-74 in Copenhagen municipality, 2026Q1 (StatBank FOLK1A)
- **Rate**: (1,438 / 515,913) x 100,000 = 278.7

---

## Step 4: Air Pollution (Optional — Recommended)

| Field | Value | Source |
| ----- | ----- | ------ |
| PM2.5 annual mean | **9.8 µg/m³** | IQAir / European Environment Agency, 2024 estimate for Copenhagen |

This is nearly 2x the WHO 2021 guideline of 5 µg/m³ but well below the EU limit of 20 µg/m³. Including air pollution in the assessment captures the negative health effects of inhaling traffic-related pollution while walking/cycling — a realistic counterweight to the physical activity benefits.

When the HEAT tool asks about cycling/walking location:

- **Proportion in traffic**: Use 50% (default) — Nørrebro has a mix of on-road cycling lanes and park/path routes

---

## Step 5: Road Crashes (Optional)

| Field | Value | Source |
| ----- | ----- | ------ |
| Cycling fatality rate | **15.9 per billion km** | ITF/OECD exposure-adjusted data for Denmark (~2013-2018) |
| Walking fatality rate | Use HEAT Denmark default | Built into HEAT tool |

Denmark has among the lowest cycling fatality rates in Europe. Including this module provides a complete picture — the small negative effect of crash risk alongside the large positive effect of physical activity.

---

## Parameters You Can Leave as HEAT Defaults

These are built into the tool and don't need local data:

| Parameter | Walking | Cycling | Note |
| --------- | ------- | ------- | ---- |
| Relative risk of death | 0.89 | 0.90 | From meta-analysis (Kelly et al., 2014) |
| Reference duration | 168 min/week | 100 min/week | At which the relative risk applies |
| Benefits cap | 30% | 45% | Max mortality reduction |
| Value of Statistical Life | HEAT default for Denmark | HEAT default for Denmark | ~EUR 2.1M, benefit-transferred from OECD |
| Discount rate | 4% | 4% | Standard for Danish public projects |

---

## Quick Entry Checklist

When you open the HEAT web tool:

1. Select **Denmark**, **Copenhagen**, **Sub-city**
2. Choose **Walking** or **Cycling** (run separately)
3. Enter modal share: **21%** (walking) or **28%** (cycling)
4. Enter population: **63,529** (walking, 20-74) or **59,605** (cycling, 20-64)
5. Enter mortality rate: **278.7** per 100,000
6. Enable air pollution module: **9.8 µg/m³** PM2.5
7. Enable road crashes module: **15.9** per billion km (cycling)
8. Review and run

---

## Data Limitations

- **Modal share is Copenhagen-wide**, not Nørrebro-specific. Nørrebro likely has higher active transport shares.
- **Mortality rate is Copenhagen municipality**, not Nørrebro. Sub-municipal health data requires formal application.
- **Modal share data is from 2018**. The 2022 Bicycle Account suggests cycling has increased since then.
- **HEAT focuses on adults only** (20-74 for walking, 20-64 for cycling). Benefits to children and older adults are not captured.
- **HEAT uses all-cause mortality**, which is conservative — it doesn't capture morbidity benefits (reduced disease burden without death).
