# Database

PostgreSQL 12 + PostGIS, running in Docker, with pgAdmin next to it.
Everything the notebooks read comes from this database.

## Files

| File | Role |
| --- | --- |
| `Dockerfile` | `postgres:12` with the PostGIS extension packages installed |
| `docker-compose.yml` | The `db` service (port 5432) and the `pgadmin` service (port 5050) |
| `init.sql` | Schema for the relational tables — run by `pipeline/load_database.ipynb` |
| `railway.sql` | Schema for the geospatial `railway` table — run by `eda/railway_delay_map.ipynb` |

## Start it

```bash
docker-compose up --build -d
```

Run this from inside `db/` — the compose file uses `context: .`, so it expects
the `Dockerfile` to be its own neighbour.

The data lives in the named Docker volume `data`, so it survives
`docker-compose down`. To wipe the database and start over, use
`docker-compose down -v`.

## Connect

**From Python / the notebooks:**

```
host=localhost port=5432 dbname=postgres user=postgres password=postgres
```

**From pgAdmin:** open <http://localhost:5050>, log in with `a@a.com` / `a`,
then *Add New Server* → *Connection* tab:

```
Host name/address:    localhost
Port:                 5432
Maintenance Database: postgres
Username:             postgres
Password:             postgres
```

All notebooks use `DB_PASSWORD = "postgres"`, matching the PostgreSQL service
configured in `docker-compose.yml`.

## Schema

`init.sql` creates:

| Table | Rows | Description |
| --- | --- | --- |
| `REGION` | 5 | Wallonie, Vlaanderen, Brussels, Foreign Country, Unknown |
| `SERVICE` | 9 | Train operators (SNCB/NMBS, Eurostar, Captrain, …) |
| `STATIONS` | 817 | Station id, name, region, latitude, longitude |
| `RELATION` | 216 | Relation label plus a `type` code (S / P / L / IC / EXTRA / international / ICT) |
| `TRAIN_DATA` | ~243 M | One row per train **stop**, with a `BIGSERIAL` id: planned/real arrival and departure times, delays in seconds, line numbers, and foreign keys to `STATIONS`, `RELATION` and `SERVICE` |
| `type_day` | 4 018 | One row per day: `holiday` (0 none / 1 school / 2 public), `weekend`, `day_after_rest` |
| `province` | 11 | The 11 Belgian provinces, mapped to a region |
| `WEATHER` | ~1.05 M | Hourly weather per province: temperature, dewpoint, humidity, precipitation, snowfall, wind direction and speed, pressure |
| `imported_train_files` | One row per loaded monthly file | Transactional import checkpoints: filename, row count and last stop id |

`railway.sql` creates:

| Table | Description |
| --- | --- |
| `railway` | `MULTILINESTRING(4326)` geometry of every line section, with `line_number` and `ptcarfrom` |

### Notes on `TRAIN_DATA`

- `delay_arrival` and `delay_departure` are in **seconds**. SNCB considers a
  train late from **6 minutes (360 s)**; the map notebooks use a 300 s threshold.
- The `id` column matters: every notebook that reconstructs a trip relies on
  `ORDER BY td.id` to get the stops of a trip in the right order. It is assigned
  by `pipeline/load_database.ipynb`, which numbers rows continuously across the
  monthly files and records completed files in `imported_train_files`.
- `ptcar_name` is the *station where the measurement was taken* (the stop),
  while `station_departure` / `station_arrival` are the endpoints of the whole
  trip. All three are foreign keys to `STATIONS`.
- `init.sql` enables PostGIS and creates the `STATIONS.geom` point column.
  `pipeline/load_database.ipynb` fills it from longitude and latitude when
  loading stations. The map and line notebooks therefore need no manual schema
  changes on a fresh database.
- Schema initialization can be rerun. Reference/weather tables that already
  contain data are left in place, and monthly files with checkpoints are skipped.
  To apply updated reference CSVs to an existing database, reload those tables
  explicitly or rebuild into a new database.
- A legacy database with `train_data` rows but no checkpoints is not automatically
  reimported. Its completed-file history must be migrated first, or the dataset
  can be loaded into a new database. The old `last_id.txt` file is not used.
