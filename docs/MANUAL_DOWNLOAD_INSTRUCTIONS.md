# Manual Download Instructions - Copenhagen Districts

If the automated download script fails due to network restrictions, follow these manual download instructions.

---

## Option 1: Direct WFS Download (Recommended)

### Step 1: Download via Browser or curl

**WFS URL:**
```
https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:bydel&outputFormat=json&SRSNAME=EPSG:4326
```

**Method A - Browser:**
1. Copy the URL above
2. Paste into your browser
3. The GeoJSON file will download automatically
4. Save as `copenhagen_bydele.geojson` in your Downloads folder

**Method B - curl (Command line):**
```bash
curl -o copenhagen_bydele.geojson \
  "https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:bydel&outputFormat=json&SRSNAME=EPSG:4326"
```

### Step 2: Import and Process

Move the downloaded file to your project and process it:

```bash
# Move to project directory
mv ~/Downloads/copenhagen_bydele.geojson /home/user/healthy-transport/

# Process and convert to GeoPackage
python scripts/import_manual_download.py copenhagen_bydele.geojson
```

The script will:
- ✓ Load the GeoJSON file
- ✓ Reproject to EPSG:25832 (Danish CRS)
- ✓ Clean and standardize column names
- ✓ Display all 10 districts
- ✓ Save as `kk_copenhagen_bydele_YYYYMMDD.gpkg` in `data/raw/boundary/`

---

## Option 2: OpenData.dk Portal

### Step 1: Visit the Dataset Page

Go to: https://www.opendata.dk/city-of-copenhagen/bydele

### Step 2: Download Options

The page offers multiple download formats:
- **GeoJSON** (Recommended)
- **Shapefile** (.zip containing .shp, .shx, .dbf, .prj)
- **CSV** (with WKT geometry)

Click the download button for your preferred format.

### Step 3: Process the Data

```bash
# If you downloaded GeoJSON
python scripts/import_manual_download.py ~/Downloads/bydele.geojson

# If you downloaded Shapefile (extract .zip first)
unzip ~/Downloads/bydele.zip -d ~/Downloads/bydele/
python scripts/import_manual_download.py ~/Downloads/bydele/bydele.shp
```

---

## Option 3: Automated Script (When Network Access Available)

If you have proper network access (not restricted by proxy/firewall):

```bash
# Run the automated download script
python scripts/download_copenhagen_districts.py

# Or specify output location and format
python scripts/download_copenhagen_districts.py \
  --output data/raw/boundary \
  --format gpkg
```

---

## Expected Output

After successful import, you should have:

**File:** `data/raw/boundary/kk_copenhagen_bydele_20260210.gpkg`

**Contents:** 10 Copenhagen districts:
1. Indre By
2. Østerbro
3. **Nørrebro** ← Our target area!
4. Vesterbro/Kongens Enghave
5. Valby
6. Vanløse
7. Brønshøj-Husum
8. Bispebjerg
9. Amager Øst
10. Amager Vest

---

## Next Steps

### 1. Open in QGIS

```bash
# Launch QGIS and add the layer
qgis data/raw/boundary/kk_copenhagen_bydele_20260210.gpkg
```

### 2. Explore the Data

- Check district boundaries
- Verify attribute data (names, codes, etc.)
- Identify Nørrebro polygon
- Check coordinate system (should be EPSG:25832)

### 3. Extract Nørrebro Boundary

Create a separate file with just Nørrebro for clipping other datasets:

```python
import geopandas as gpd

# Load districts
districts = gpd.read_file('data/raw/boundary/kk_copenhagen_bydele_20260210.gpkg')

# Filter to Nørrebro
norrebro = districts[districts['bydel_navn'] == 'Nørrebro']

# Save as separate file
norrebro.to_file('data/processed/norrebro_boundary.gpkg', driver='GPKG')

print(f"Nørrebro area: {norrebro.geometry.area.values[0] / 1_000_000:.2f} km²")
```

### 4. Update CLAUDE.MD

Check off the completed items in your project checklist:
- ✓ Section 8: Define Nørrebro Boundary
- ✓ Downloaded official boundary
- ✓ Explored in QGIS

---

## Troubleshooting

### Issue: "No module named 'geopandas'"
```bash
pip install geopandas shapely pandas
```

### Issue: File not recognized
Check the file extension and try:
```bash
ogrinfo -so <your_file>  # Check file info
```

### Issue: Geometry errors
The import script will automatically:
- Fix invalid geometries
- Reproject to correct CRS
- Handle various geometry formats

---

## Alternative Data Sources (If Above Methods Fail)

1. **GADM Denmark Districts:**
   - https://gadm.org/download_country.html
   - Select Denmark, Level 3 (finest resolution)

2. **OpenStreetMap:**
   - Use Overpass Turbo: https://overpass-turbo.eu/
   - Query for Copenhagen administrative boundaries

3. **Contact Copenhagen Municipality:**
   - Email: bydata@kk.dk
   - Request: Bydele (city districts) boundaries

---

## Questions?

If you encounter issues:
1. Check the file path and format
2. Verify QGIS can open the file
3. Review error messages from the import script
4. Contact data provider at bydata@kk.dk
