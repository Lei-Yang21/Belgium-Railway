# Pipeline — from raw open data to a loaded database

Run the steps in the order below. Steps 1–2 are scripts, the rest are notebooks.
Notebooks expect their own folder as the working directory; the scripts resolve
their paths from the project root, so they can be launched from anywhere.

Almost all of the reference CSVs are already committed in
[`../data/reference/`](../data/reference/), so in practice you only need
steps 1, 2 and 9 to rebuild a working database.

## 1. `download_punctuality_data.py` — download the punctuality data

Reads the list of monthly links in `data/reference/monthly_punctuality_urls.csv` (one row per
month, 2014-01 → 2024-12) and downloads every raw Infrabel punctuality CSV into
`data/raw/`. About 37 GB — the folder is git-ignored.

```bash
python pipeline/download_punctuality_data.py
```

## 2. `compress_punctuality_data.py` — shrink and normalise the raw files

For each monthly file:

- keeps only the 15 columns that are common to all files;
- parses `DATDEP` as a date;
- replaces the string columns `RELATION`, `TRAIN_SERV` and `PTCAR_LG_NM_NL` by
  integer ids, using the maps stored in `RELATION.csv`, `TRAIN_SERV.csv` and
  `UNIQUE_STATION.csv` (it builds those three files on the first run if they are
  missing);
- splits `RELATION_DIRECTION` (`"… : A -> B"`) into `station_departure` and
  `station_arrival`, also mapped to station ids;
- renames every column to the database naming.

Output goes to `data/cleaned/` (git-ignored, ~21 GB), one file per month, ready
for `COPY`.

```bash
python pipeline/compress_punctuality_data.py
```

> This rewrites every file in `data/cleaned/`. It takes hours — don't launch it
> to "check something", and don't interrupt it: a killed run leaves the file it
> was writing truncated.

## 3. `geolocate_stations.ipynb` — geolocate the stations

Takes `UNIQUE_STATION.csv` (id → station name) and attaches to each station a
**region** and a **latitude/longitude**:

- a first pass queries Nominatim (`geopy`) for the region of each station name;
- coordinates come from the Infrabel station export `data/geo/coordinates.csv`,
  melted over its ten name variants (FR/NL, short/medium/full) so a station can
  be matched under any of its spellings;
- a long manual block then fixes the many stations that geocoding got wrong or
  missed — mostly freight yards, connections, and foreign stations.

Writes `data/reference/stations_with_regions.csv` (the `STATIONS` table) and
`data/reference/REGION.csv`. Intermediate files land in `data/interim/`.

## 4. `classify_train_relations.ipynb` — classify the relations

Adds a `type` column to `RELATION.csv` based on the prefix of the relation label:
`S` → 1 (suburban), `P` → 2 (rush hour), `L` → 3 (local), `IC` → 4 (intercity),
`EXTRA` → 5, `ICE`/`T`/`INT` → 6 (international), `ICT` → 7. Everything else
stays 0.

## 5. `build_calendar.ipynb` — build the calendar table

Generates one row per day from 2014-01-01 to 2024-12-31 with:

- `holiday`: 0 = ordinary day, 1 = school holiday (hard-coded ranges following
  the French-speaking community calendar), 2 = Belgian public holiday (via the
  `holidays` package);
- `weekend`: Saturday or Sunday;
- `day_after_rest`: first working day after a weekend or public holiday.

Writes `data/reference/dates_2014_2024.csv` (the `type_day` table).

The school calendar is a shared modeling proxy; it does not encode separate
school holidays for every Belgian community. Corrections to the 2015 and
2023–2024 ranges follow the official calendars
([2015–2016](https://gallilex.cfwb.be/document/pdf/40601_000.pdf),
[2022–2024](https://www.gallilex.cfwb.be/document/pdf/50303_000.pdf)).
The committed CSV includes these corrections and flags the first working day
after a weekend/public holiday even during school holidays.

## 6. `compute_province_centroids.ipynb` — centroid of each Belgian province

Loads the GADM level-2 shapefile `data/geo/gadm41_BEL_2.shp` with GeoPandas and
writes the centroid of each of the 11 provinces to
`data/geo/belgium_provinces_centroids.csv`. Those centroids are the points the
weather is fetched for.

## 7. `fetch_province_weather.ipynb` — hourly weather per province *(final version)*

For each province centroid, fetches hourly observations from **Meteostat**
(2014-01-01 → 2025-01-01): temperature, dewpoint, relative humidity,
precipitation, snowfall, wind direction, wind speed, pressure. Columns with too
many gaps (`coco`, `wpgt`) are dropped, `snow` and `prcp` gaps are filled with 0.

Writes `data/weather/hourly_weather_data.csv` (~1.05 M rows) — this is what ends
up in the `WEATHER` table — and `data/reference/province_mapping.csv`, which
numbers the 11 provinces and attaches each one to its region (the `province`
table).

## 8. `fetch_region_weather.ipynb` — hourly weather per region *(earlier version)*

The first attempt: **Open-Meteo** archive API at one point per region (Wallonia,
Flanders, Brussels), with a wider set of variables (cloud cover, radiation,
evapotranspiration, wind gusts). Writes the three per-region files and their
concatenation `data/weather/belgium_hourly_weather_2014_2024.csv`.

Kept because [`../eda/region_weather_analysis.ipynb`](../eda/region_weather_analysis.ipynb)
is based on it, but it is **not** the data loaded into the database. It needs a
`time.sleep(100)` between calls to stay under the Open-Meteo rate limit.

## 9. `load_database.ipynb` — load everything into PostgreSQL

Runs `db/init.sql`, then `COPY`s each file into its table:

| Source | Table |
| --- | --- |
| `data/reference/REGION.csv` | `region` |
| `data/reference/TRAIN_SERV.csv` | `service` |
| `data/reference/stations_with_regions.csv` | `stations` |
| `data/reference/RELATION.csv` | `relation` |
| every file in `data/cleaned/` | `train_data` |
| `data/reference/dates_2014_2024.csv` | `type_day` |
| `data/reference/province_mapping.csv` | `province` |
| `data/weather/hourly_weather_data.csv` | `weather` |

The database must already be running (see [`../db/README.md`](../db/README.md)).

The `train_data` load is the long one — hundreds of millions of rows. Each
monthly file gets continuous stop ids and is committed together with its
`imported_train_files` checkpoint. A failed file is rolled back; restarting skips
completed filenames and continues after the database's current maximum id.
Keep monthly files unchanged after importing them. Temporary files left by the
older loader (`temp_*.csv`) are ignored.

Schema initialization is repeatable. Reference and weather tables that already
contain data are skipped, so restarting does not duplicate them. Station geometry
is populated automatically. An older `train_data` load without checkpoints needs
its completed-file history migrated or a fresh database; `last_id.txt` is no
longer consulted.

The geospatial `railway` table is **not** loaded here; it is created at the top
of [`../eda/railway_delay_map.ipynb`](../eda/railway_delay_map.ipynb).
