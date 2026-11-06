# Exploratory data analysis

Four notebooks, plus one that looks at the raw files before they ever reach the
database. The three "real" EDA notebooks query PostgreSQL, so
[`../db/`](../db/README.md) must be running and
[`../pipeline/load_database.ipynb`](../pipeline/load_database.ipynb) must have finished.

| Notebook | Subject |
| --- | --- |
| `raw_dataset_overview.ipynb` | The raw Infrabel files, before cleaning |
| `train_delay_analysis.ipynb` | Delays: over time, by station, relation, service, day type |
| `province_weather_analysis.ipynb` | The weather data actually loaded in the database |
| `region_weather_analysis.ipynb` | The earlier, region-level weather data |
| `railway_delay_map.ipynb` | The geospatial dimension: lines and stations on a map |

## `raw_dataset_overview.ipynb`

Checks that all ~130 monthly files share the same columns, measures the memory
cost of the raw types, and writes the per-column missing-value report to
[`../data/interim/missing_values.txt`](../data/interim/missing_values.txt).
This is what motivated `pipeline/compress_punctuality_data.py`.

## `train_delay_analysis.ipynb` — delays

The main EDA. What it establishes:

- `delay_arrival` and `delay_departure` behave almost identically, so either can
  stand for "the delay of a train".
- **Yearly / monthly**: years follow a similar shape, except 2020–2021 (Covid).
  A spike in June, October and November; a dip in July–August.
- **Day of week**: weekdays are worse than weekends; Monday and Friday are the
  worst days.
- **Relations**: `EXTRA` services and international relations have the highest
  delays; local and IC trains, which are far more frequent, the lowest. 216
  relations in total, IC being the most common and international/special the
  rarest.
- **Stations**: the busiest stations are all in Brussels. ~400 stations have
  fewer than 10 stops recorded — mostly `EXTRA` services and rare local trains.
- **Services**: SNCB/NMBS covers ~90 % of the trips; 4 of the 8 other services
  are used extremely rarely. Cross-border services have a higher average delay.
- **Threshold**: using SNCB's own definition (late from 6 minutes), **11.98 %**
  of the trips in the dataset were late.
- **Outlier days** were traced back to real events: 2014-12-15 (strike),
  2023-11-02 (storm), 2016-10-05 (bomb alert), 2024-01-18 (cyberattack).
- **Weather correlation** is weak overall; relative humidity, high cloud cover
  and a few other variables are the least uninteresting.
- **Day type**: ordinary days have higher average delays than weekends and
  school holidays, and public holidays are lower still — fewer trains, less
  congestion.
- **Stations over time**: the number of active stations grows over the period,
  except between 2020 and 2022 where international stops drop out.

## `province_weather_analysis.ipynb` — weather (final)

EDA on `data/weather/hourly_weather_data.csv`, the Meteostat per-province data
that is loaded into the `WEATHER` table. No null values left after the pipeline.
Compares two outlier-removal strategies and settles on the **z-score** method:
the quartile method would discard more than half of the dataset. Notes that the
variables live on very different scales, and that the low correlation between
provinces suggests the weather is fairly homogeneous across the country.

## `region_weather_analysis.ipynb` — weather (earlier version)

The same analysis on the Open-Meteo, region-level dataset
(`data/weather/belgium_hourly_weather_2014_2024.csv`), which has more variables
(cloud cover by layer, radiation, evapotranspiration). Superseded by the
province version, kept because the early analysis was based on it.

## `railway_delay_map.ipynb` — the geospatial dimension

1. Creates the `railway` table from [`../db/railway.sql`](../db/railway.sql) and
   loads Infrabel's `lijnsecties.geojson` into it with `GeoPandas.to_postgis`,
   keeping `geometry`, `label` (line number) and `ptcarfrom`.
2. Joins the share of delayed trains (`delay_arrival > 300 s`) per line onto the
   line geometries and plots it as a heatmap over the Belgian border.
3. Does the same per station (stations with at least 100 recorded stops).

Requires PostGIS, which the [`../db/Dockerfile`](../db/Dockerfile) installs.
