# Data Sources

URLs, APIs, authentication, and download scripts for all project data.

---

## Primary Geospatial Sources

| Source | URL | Used For |
|---|---|---|
| Dataforsyningen (SDFI) | https://dataforsyningen.dk/ | Official Danish geographic data |
| Open Data DK | https://www.opendata.dk/ | Copenhagen boundaries, road centre lines |
| Statistics Denmark | https://www.dst.dk/ | Population, demographics, mortality |
| OpenStreetMap | https://www.openstreetmap.org/ | Pedestrian/cycling network |
| Copenhagen Municipality | https://data.kk.dk/ | City open data portal |

## Health Data Sources

| Source | URL | Level | Access |
|---|---|---|---|
| Sundhedsdatabanken (eSundhed) | https://sundhedsdatabank.dk/ | Municipality | Free, manual download |
| Danskernes Sundhed | https://www.danskernessundhed.dk/ | Municipality | Free, interactive viewer |
| StatBank Denmark | https://www.statbank.dk/ | National/Municipality | Free, API |
| WHO HEAT Tool | https://www.heatwalkingcycling.org | Framework | Free, web tool |
| WHO HEAT 2024 Guide | https://www.who.int/europe/publications/i/item/9789289058377 | Reference | PDF |

## API Endpoints

| API | URL | Layer/Entity | Auth |
|---|---|---|---|
| BBR WFS | `https://wfs.datafordeler.dk/BBR/BBR_WFS/1.0.0/WFS` | `bbr_v001:bygning_current` | `.env` credentials |
| DAR File Download | `https://api.datafordeler.dk/FileDownloads/GetFile` | Entity: `Adressepunkt`, municipality: 0101 | `.env` credentials |
| Copenhagen Municipality WFS | `https://wfs-kbhkort.kk.dk/k101/ows` | Multiple layers (see below) | None (free) |
| Rejseplanen GTFS | `https://www.rejseplanen.info/labs/GTFS.zip` | National GTFS feed | None (free) |
| StatBank Denmark API | `https://api.statbank.dk/v1/` | Tables: DODA1, FOD207, FOLK1A | None (free) |

**Datafordeleren credentials**: `DATAFORDELEREN_USERNAME` and `DATAFORDELEREN_PASSWORD` in `.env`

## Copenhagen Municipality WFS Layers

All from `wfs-kbhkort.kk.dk/k101/ows`:

| Layer | Used In |
|---|---|
| `k101:cykelsti` | Cycling (raw, not used for analysis) |
| `k101:cykeldata` | Cycling network |
| `k101:cykelstativ` | Bike parking |
| `k101:parkregister` | Parks |
| `k101:park_groent_omr_oversigtskort` | Green areas overview |
| `k101:legeplads` | Playgrounds |
| `k101:blaa_cykelfelt` | Blue cycle crossings (available, not downloaded) |
| `k101:park_groent_omr_omegn` | Surrounding green areas (available, not downloaded) |
| `k101:gadetraer` | Street trees (available, not downloaded) |

## Download Scripts

| Script | Datasets | Method |
|---|---|---|
| `scripts/download/download_copenhagen_districts.py` | Boundary | WFS |
| `scripts/download/download_bbr_dar.py` | BBR buildings + DAR addresses | WFS + File API |
| `scripts/download/download_pedestrian_network.py` | OSM network | osmnx |
| `scripts/download/download_cycling.py` | Cycling infra (3 layers) | KK WFS |
| `scripts/download/download_greenspaces.py` | Parks + playgrounds (3 layers) | KK WFS |
| `scripts/download/download_gtfs.py` | GTFS national feed | HTTP download |
| `scripts/download/download_health.py` | StatBank DODA1 + FOD207 | StatBank API |

## Integration Scripts

| Script | Input | Output |
|---|---|---|
| `scripts/integrate/integrate_buildings.py` | Footprints + BBR + DAR + Neighbourhoods | `data/integrated/norrebro_buildings.gpkg` |

**Manual downloads** (documented in `docs/health_data_download_guide.md`):
- eSundhed chronic disease XLSX
- Danskernes Sundhed survey CSVs (7 indicators)
- WHO HEAT user guide PDF

## DAR Technical Standard Reference

Documentation: https://danmarksadresser.dk/adressedata/kodelister/teknisk-standard

## BBR Code Lists Reference

Documentation: https://teknik.bbr.dk/kodelister
