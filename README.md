# PROJ0021-1 — Data Science Project

**Improving Railway Reliability in Belgium through Delay Prediction Models**
University of Liège, 2024–2025.

Predicting **train delays in Belgium** from ten years of SNCB/Infrabel punctuality
records (2014–2024), enriched with hourly weather, calendar information and the
geography of the Belgian railway network.

Everything is stored in a PostgreSQL/PostGIS database that runs in Docker; the
analysis and the models are Jupyter notebooks that query that database.

## What the project answers

1. **How do delays behave?** Over the years, months, days of the week, hours,
   stations, lines, relations and train services — see [`eda/`](eda/).
2. **Can delays be explained by weather and calendar alone?** Regression and
   classification on aggregated (day / hour) delays — see [`modeling/`](modeling/).
3. **Can the delay at the *next* stops of a trip be predicted from the delay so
   far?** Multi-output, chained and recurrent models on a single 57-stop line
   (Brussel-Zuid → Luxembourg) — see [`modeling/`](modeling/).

### Short answer

Weather and calendar alone explain very little. On a random split, a random
forest reaches R² ≈ 0.29 on the daily average delay, and ≈ 0.42 once the 5 % most
extreme days (strikes, storms) are excluded. But **split the data by time**
— train before 2020, test after 2022 — and it collapses to R² ≈ 0; averaged over
10 year-folds it is **−0.37**. The model does not generalise across time.

What *is* predictive is the delay a train has already accumulated. One stop
ahead, R² > 0.9; over a full 56-stop horizon, R² ≈ 0.45–0.55. The details and
the caveats are in [`modeling/README.md`](modeling/README.md).

The metrics and saved notebook outputs above describe the original experiments.
The calendar and modeling code have since been corrected; updated results require
reloading the corrected calendar and rerunning the analyses and models.

## Repository layout

| Folder | Contents |
| --- | --- |
| [`data/`](data/README.md) | All CSV / GeoJSON / shapefile inputs, split by role (`reference`, `weather`, `geo`, `interim`) plus the git-ignored `raw/` and `cleaned/` dataset folders |
| [`db/`](db/README.md) | Docker image, `docker-compose.yml` and the SQL schemas (`init.sql`, `railway.sql`) |
| [`pipeline/`](pipeline/README.md) | Data acquisition, cleaning, enrichment and loading into the database |
| [`eda/`](eda/README.md) | Exploratory data analysis: trains, weather, and the geospatial dimension |
| [`modeling/`](modeling/README.md) | Regression, classification and the station-ahead delay-propagation models |

## Quickstart

Run each command from the folder it lives in, and start notebooks with their own
directory as the working directory (the default in Jupyter/VS Code). Paths inside
the notebooks are relative to that directory.

### 1. Start the database

```bash
cd db && docker-compose up --build -d
```

PostgreSQL (with PostGIS) on `localhost:5432`, pgAdmin on `localhost:5050`.
Credentials are in [`db/README.md`](db/README.md).

### 2. Build the dataset

```bash
python pipeline/download_punctuality_data.py
```

```bash
python pipeline/compress_punctuality_data.py
```

The first downloads 132 monthly punctuality files from Infrabel into `data/raw/`
(~37 GB); the second maps every string column to an integer id and writes the
result to `data/cleaned/` (~21 GB). Both folders are git-ignored.

### 3. Load everything into the database

Run [`pipeline/load_database.ipynb`](pipeline/load_database.ipynb) and wait for it to
finish. It creates the schema from `db/init.sql` and `COPY`s every reference
table, the cleaned punctuality files and the weather data. The `train_data` load
is resumable — completed files are recorded in the database table
`imported_train_files`, in the same transaction as their data.

The geospatial `railway` table is created separately, at the top of
[`eda/railway_delay_map.ipynb`](eda/railway_delay_map.ipynb).

### 4. Explore and model

Open the notebooks in [`eda/`](eda/) and [`modeling/`](modeling/). They only need
a running database — no notebook depends on another notebook's in-memory state.

## Requirements

Use Python 3.12 and install the dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

[`requirements.txt`](requirements.txt) includes JupyterLab and the notebook
kernel, with compatibility bounds for the APIs used by the existing code.

Docker and Docker Compose are required for the database.

## Data sources

- **Punctuality** — [Infrabel open data — monthly raw punctuality files](https://opendata.infrabel.be/explore/dataset/stiptheid-gegevens-maandelijksebestanden/information/)
  (2014-01 → 2024-12). Download links in
  [`data/reference/monthly_punctuality_urls.csv`](data/reference/monthly_punctuality_urls.csv).
- **Weather** — [Meteostat](https://meteostat.net/) hourly observations at the
  centroid of each of the 11 Belgian provinces (final version), and
  [Open-Meteo](https://open-meteo.com/) archive API for a first, region-level
  version.
- **Station coordinates** — Infrabel "points d'arrêt" export
  ([`data/geo/coordinates.csv`](data/geo/coordinates.csv)).
- **Railway lines** — Infrabel `lijnsecties.geojson`.
- **Province boundaries** — [GADM](https://gadm.org/) level-2 shapefile for Belgium.
- **Holidays** — Belgian public holidays via the `holidays` package, school
  holidays hard-coded in [`pipeline/build_calendar.ipynb`](pipeline/build_calendar.ipynb).

## Authors

- Hormat-Allah Saïd
- Lei Yang
- Houyon Manuel

## License

The project code is licensed under the [MIT License](LICENSE).
Third-party datasets remain subject to their respective source licenses.
