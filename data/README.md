# Data

Four committed folders, plus two git-ignored ones that the pipeline fills in.

| Folder | What's in it | In git? |
| --- | --- | --- |
| `reference/` | Small lookup tables — the ones loaded into the database | yes |
| `weather/` | Hourly weather series | yes |
| `geo/` | Geometries and coordinates | yes |
| `interim/` | Throwaway intermediates and reports, kept for traceability | yes |
| `raw/` | Raw monthly Infrabel punctuality files | **no** (several GB) |
| `cleaned/` | The same files after `pipeline/compress_punctuality_data.py` | **no** |

---

## `reference/`

| File | Columns | Produced by | Loaded into |
| --- | --- | --- | --- |
| `monthly_punctuality_urls.csv` | `Mois`, `Lien vers les données` | export from the Infrabel open-data portal | — (input to the downloader) |
| `REGION.csv` | `id`, `name` | `pipeline/geolocate_stations.ipynb` | `region` |
| `TRAIN_SERV.csv` | `ID`, `TRAIN_SERV` | `pipeline/compress_punctuality_data.py` | `service` |
| `RELATION.csv` | `ID`, `RELATION`, `type` | `compress_punctuality_data.py` + `classify_train_relations.ipynb` | `relation` |
| `UNIQUE_STATION.csv` | `ID`, `STATION` | `pipeline/compress_punctuality_data.py` | — (input to `geolocate_stations.ipynb`) |
| `stations_with_regions.csv` | `ID`, `STATION`, `REGION`, `Latitude`, `Longitude` | `pipeline/geolocate_stations.ipynb` | `stations` |
| `province_mapping.csv` | `ID`, `province`, `Region` | `pipeline/fetch_province_weather.ipynb` | `province` |
| `dates_2014_2024.csv` | `date`, `holiday`, `weekend`, `day_after_rest` | `pipeline/build_calendar.ipynb` | `type_day` |
| `passengers_count.csv` | `YEAR`, `AMOUNT` (millions of passengers) | added by hand from an external source | — |

`passengers_count.csv` is context data used in the written report; no notebook
reads it.

### Region codes

`0` Unknown · `1` Wallonie · `2` Vlaanderen · `3` Brussels · `4` Foreign country

### Relation types

`0` other · `1` S (suburban) · `2` P (rush hour) · `3` L (local) · `4` IC ·
`5` EXTRA · `6` international (ICE / T / INT) · `7` ICT

---

## `weather/`

| File | Source | Granularity | Used by |
| --- | --- | --- | --- |
| `hourly_weather_data.csv` | Meteostat | 11 provinces × hourly, 2014→2025 | **the `weather` table**, `eda/province_weather_analysis.ipynb` |
| `belgium_hourly_weather_2014_2024.csv` | Open-Meteo | 3 regions × hourly, concatenated | `eda/region_weather_analysis.ipynb` |
| `Brussels_…csv`, `Flanders_…csv`, `wallonia_…csv` | Open-Meteo | one file per region | `pipeline/fetch_region_weather.ipynb` |

The Meteostat file is the one that matters; the Open-Meteo files are the earlier
version, kept because the first milestones are based on them.

`hourly_weather_data.csv` columns: `temp`, `dwpt`, `rhum`, `prcp`, `snow`,
`wdir`, `wspd`, `pres`, `Province`, `date`, `hour` — in that order, matching the
`weather` table. The loader supplies the corresponding database column list
explicitly.

---

## `geo/`

| File | Description |
| --- | --- |
| `coordinates.csv` | Infrabel export of every stopping point (`;`-separated), with a geo point and ten name variants per station. Used to geolocate stations. |
| `lijnsecties.geojson` | Infrabel line sections — the geometry of the railway network. Loaded into the `railway` table by `eda/railway_delay_map.ipynb`. |
| `gadm41_BEL_2.*` | GADM level-2 shapefile of Belgium (provinces). The five files `.shp` / `.shx` / `.dbf` / `.prj` / `.cpg` belong together. |
| `belgium_provinces_centroids.csv` | The centroid of each province, computed from the shapefile. The points the weather is fetched for. |

---

## `interim/`

Nothing here is loaded into the database; these files are kept so the steps of
`geolocate_stations.ipynb` stay reproducible and inspectable.

| File | What it is |
| --- | --- |
| `station_name_coordinates.csv` | `coordinates.csv` melted over its ten name columns, one row per (station name variant, geo point) |
| `station_coordinates_uncorrected.csv` | Stations joined with their coordinates, **before** the manual corrections |
| `UNIQUE_STATION_REGION.csv` | Stations with the raw Nominatim region, before cleaning |
| `missing_values.txt` | Per-column missing-value report over every raw monthly file, produced by `eda/raw_dataset_overview.ipynb` |

---

## `raw/` and `cleaned/`

Both are git-ignored (see the root `.gitignore`), so they will not exist in a
fresh clone. Recreate them with:

```bash
python pipeline/download_punctuality_data.py
```

```bash
python pipeline/compress_punctuality_data.py
```

`raw/` holds one Infrabel CSV per month, 2014-01 → 2024-12, with the original
column names (`DATDEP`, `TRAIN_NO`, `RELATION`, `PTCAR_LG_NM_NL`, …) — 132 files,
~37 GB. `cleaned/` holds the same months with strings replaced by integer ids and
the columns renamed to the database schema — ~21 GB, roughly 243 million rows.

Import progress is stored in the database table `imported_train_files`
(see [`../pipeline/README.md`](../pipeline/README.md)), not in this folder.
An existing `last_id.txt` belongs to the older loader and is no longer used.
