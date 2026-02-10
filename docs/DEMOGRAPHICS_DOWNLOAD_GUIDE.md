
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
